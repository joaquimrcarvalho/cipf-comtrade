#!/usr/bin/env python3
"""Export cipf-comtrade datasets as committed snapshots for the Observable Framework site.

Spec: docs/SITE_SPECS.md §4.2 (data flow) and §5 (snapshot contracts).

Runs locally from the repo venv; reuses the comtradetools cache (cache/) and the
API key (config.ini) so no network access is needed for already-cached series.
Outputs tidy CSV + *.meta.json under site/src/data/.

Usage (from the repo root):
    venv/bin/python site/scripts/export_site_data.py
    venv/bin/python site/scripts/export_site_data.py --reporters cn mo --end 2024
    venv/bin/python site/scripts/export_site_data.py --check

Note: get_trade_flows() is called with the same defaults the notebooks use
(period_size=1) so the existing cache pickles are reused. retry_if_empty=False
avoids surprise live API retries for legitimately empty partner-year combos.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "site" / "src" / "data"

REPORTERS = {
    "cn": (156, "China"),
    "mo": (446, "Macau (RAEM)"),
    "hk": (344, "Hong Kong (RAEHK)"),
    # Taiwan (Prov. China) is reported by Comtrade as "Other Asia, nes" (code 490):
    # https://uncomtrade.org/docs/taiwan-province-of-china-trade-data/
    "tw": (490, "Taiwan (Prov. China)"),
}

# Portuguese short names for the site UI (Comtrade names are English).
PLP_NAMES_PT = {
    24: "Angola",
    76: "Brasil",
    132: "Cabo Verde",
    624: "Guiné-Bissau",
    226: "Guiné Equatorial",
    508: "Moçambique",
    620: "Portugal",
    678: "São Tomé e Príncipe",
    626: "Timor-Leste",
}

SOURCE_NOTEBOOKS = {
    "cn": "cn_plp_import_export.ipynb",
    "mo": "mo_plp_import_export.ipynb",
    "hk": "hk_plp_import_export.ipynb",
    "tw": "tw_plp_import_export.ipynb",
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("export_site_data")


def init_comtradetools():
    """Initialize comtradetools exactly like the notebooks do (from the repo root)."""
    os.chdir(REPO_ROOT)  # module uses relative paths (support/, cache/, config.ini)
    sys.path.insert(0, str(REPO_ROOT))
    import comtradetools as ctt

    ctt.setup()
    ctt.init(ctt.get_api_key())
    return ctt


def year_list(start: int, end: int) -> str:
    return ",".join(str(y) for y in range(start, end + 1))


def fetch_totals(ctt, reporter: str, partner: str, flow: str, period: str,
                 country_col: str) -> pd.DataFrame:
    """One batched getFinalData call per (reporter set, partner, flow).

    reporter/partner are comma-separated M49 codes. Uses period_size=12 (the API
    maximum per call) so a full 2003-2024 series needs only 2 calls per flow —
    unlike the notebooks' period_size=1 pattern, whose pickles have expired.
    country_col names the column identifying the PLP side of the pair
    ("partnerCode" for direct queries, "reporterCode" for mirror queries).
    Returns a (year, partner_code, value) frame.
    """
    log.info("getFinalData reporter=%s partner=%s flow=%s (%s…)", reporter, partner,
             flow, period[:18])
    df = ctt.getFinalData(
        ctt.APIKEY,
        typeCode="C",
        freqCode="A",
        reporterCode=reporter,
        partnerCode=partner,
        partner2Code=0,
        flowCode=flow,
        period=period,
        period_size=12,
        retry_if_empty=False,
        motCode=0,
        customsCode="C00",
        cmdCode="TOTAL",
        clCode="HS",
        includeDesc=False,
    )
    if df is None or df.empty:
        return pd.DataFrame(columns=["year", "partner_code", "value"])
    out = (
        df.groupby(["period", country_col])["primaryValue"]
        .sum()
        .reset_index()
        .rename(columns={"period": "year", country_col: "partner_code",
                         "primaryValue": "value"})
    )
    return out


def flows_long_frame(ctt, reporter_code: int, start: int, end: int) -> pd.DataFrame:
    """Build the D1 long table (spec §5.2) for one reporter vs all PLPs.

    Emits direct rows (reported by the reporter: X, M) and mirror rows
    (inferred from partners' reports: X<M, M<X) with explicit `basis`.
    Only 8 API calls per reporter (2 flows × 2 bases × 2 period chunks).
    """
    period = year_list(start, end)
    plp_list = ",".join(str(c) for c in PLP_NAMES_PT)
    reporter = str(reporter_code)

    # direct: reporter-reported X and M, partner = PLP
    direct_x = fetch_totals(ctt, reporter, plp_list, "X", period, "partnerCode")
    direct_m = fetch_totals(ctt, reporter, plp_list, "M", period, "partnerCode")
    # mirror: PLP-reported; their imports = our X<M, their exports = our M<X
    mirror_x = fetch_totals(ctt, plp_list, reporter, "M", period, "reporterCode")
    mirror_m = fetch_totals(ctt, plp_list, reporter, "X", period, "reporterCode")

    def basis_rows(x_df: pd.DataFrame, m_df: pd.DataFrame, basis: str) -> list:
        merged = pd.merge(x_df, m_df, on=["year", "partner_code"],
                          how="outer", suffixes=("_x", "_m")).fillna(0)
        rows = []
        for _, r in merged.iterrows():
            x, m = int(r["value_x"]), int(r["value_m"])
            code = int(r["partner_code"])
            if (x == 0 and m == 0) or code not in PLP_NAMES_PT:
                continue
            rows.append(dict(year=int(r["year"]), partner_code=code,
                             partner=PLP_NAMES_PT[code], exports=x, imports=m,
                             trade_volume=x + m, balance=x - m, basis=basis))
        return rows

    rows = basis_rows(direct_x, direct_m, "direct")
    rows += basis_rows(mirror_x, mirror_m, "mirror")
    df = pd.DataFrame(rows)
    return df.sort_values(["year", "partner_code", "basis"]).reset_index(drop=True)


def write_snapshot(df: pd.DataFrame, reporter_key: str, start: int, end: int) -> Path:
    reporter_code, reporter_name = REPORTERS[reporter_key]
    stem = f"{reporter_key}_plp_flows_{start}-{end}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / f"{stem}.csv"
    df.to_csv(csv_path, index=False)
    meta = {
        "dataset": f"{reporter_key}_plp_flows",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_notebook": SOURCE_NOTEBOOKS[reporter_key],
        "reporter_code": reporter_code,
        "reporter_name": reporter_name,
        "units": "USD (current)",
        "flow_basis": "both — see 'basis' column: 'direct' (reported by the reporter) "
                      "or 'mirror' (inferred from partners' reports, X<M / M<X)",
        "period": f"{start}-{end}",
        "rows": len(df),
        "columns": list(df.columns),
        "notes": "trade_volume = exports + imports; balance = exports - imports. "
                 "From the reporter's perspective. Source: UN Comtrade via "
                 "comtradetools.getFinalData(). An unreported flow contributes 0 "
                 "to volume/balance (the Forum Macau quadros print blank in those "
                 "cells; see the --check warnings).",
    }
    meta_path = OUT_DIR / f"{stem}.meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    log.info("wrote %s (%d rows) + meta", csv_path, len(df))
    return csv_path


def write_reference_files():
    """plp_countries.json reference dimension (spec §5.2)."""
    import comtradetools as ctt  # noqa: PLC0415 — after init, for decode_country

    rows = []
    for code, name_pt in PLP_NAMES_PT.items():
        rows.append({
            "code": code,
            "name_pt": name_pt,
            "name_en": ctt.decode_country(code),
        })
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "plp_countries.json"
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    log.info("wrote %s", path)


def check_cn_parity(csv_path: Path) -> bool:
    """Compare direct-basis China↔PLP rows against the validated Forum quadros Excel.

    The Excel (reports/cn_plp_trocas_*.xlsx) was validated against the tables
    published by Forum Macau. Non-NaN Excel cells must match exactly; Excel NaN
    cells (missing reporter data) only produce a warning when we carry a
    non-zero value (fillna(0) methodological difference: missing vs zero).
    """
    candidates = sorted((REPO_ROOT / "reports").glob("cn_plp_trocas_*.xlsx"))
    if not candidates:
        log.error("parity check: no reports/cn_plp_trocas_*.xlsx found")
        return False
    ref = pd.read_excel(candidates[-1])
    log.info("parity check against %s", candidates[-1].name)

    df = pd.read_csv(csv_path)
    df = df[df["basis"] == "direct"]
    # Excel partnerDesc is in English; map via comtradetools encode for robustness
    import comtradetools as ctt  # noqa: PLC0415

    ok = True
    checked = skipped = 0
    for _, r in ref.iterrows():
        code = ctt.encode_country(r["partnerDesc"])
        if not isinstance(code, int):
            log.error("unknown partner in Excel: %s", r["partnerDesc"])
            ok = False
            continue
        row = df[(df["year"] == r["refYear"]) & (df["partner_code"] == code)]
        if row.empty:
            log.error("missing in CSV: %s %s", r["refYear"], r["partnerDesc"])
            ok = False
            continue
        row = row.iloc[0]
        for excel_col, csv_col in [("Exportações", "exports"), ("Importações", "imports"),
                                   ("Trocas", "trade_volume"), ("Saldo", "balance")]:
            expected = r[excel_col]
            got = row[csv_col]
            if pd.isna(expected):
                skipped += 1
                if got != 0:
                    log.warning("Excel NaN but CSV has %s=%s (%s %s)",
                                csv_col, got, r["refYear"], r["partnerDesc"])
                continue
            checked += 1
            if int(expected) != int(got):
                log.error("MISMATCH %s %s %s: excel=%s csv=%s",
                          r["refYear"], r["partnerDesc"], csv_col, int(expected), int(got))
                ok = False
    log.info("parity: %d cells compared, %d Excel-NaN cells skipped, result=%s",
             checked, skipped, "OK" if ok else "FAILED")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reporters", nargs="+", choices=REPORTERS.keys(), default=["cn"],
                    help="reporters to export (default: cn)")
    ap.add_argument("--start", type=int, default=2003)
    ap.add_argument("--end", type=int, default=2024,
                    help="default 2024: matches the validated Forum quadros Excel and "
                         "the local cache; later years may trigger live API calls")
    ap.add_argument("--check", action="store_true",
                    help="run parity check vs reports/cn_plp_trocas_*.xlsx (cn only)")
    args = ap.parse_args()

    ctt = init_comtradetools()
    write_reference_files()

    overall_ok = True
    for key in args.reporters:
        df = flows_long_frame(ctt, REPORTERS[key][0], args.start, args.end)
        if df.empty:
            log.error("empty dataset for reporter %s — aborting (guard against "
                      "partial API data)", key)
            overall_ok = False
            continue
        csv_path = write_snapshot(df, key, args.start, args.end)
        if args.check and key == "cn":
            overall_ok = check_cn_parity(csv_path) and overall_ok

    sys.exit(0 if overall_ok else 1)


if __name__ == "__main__":
    main()
