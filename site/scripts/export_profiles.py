#!/usr/bin/env python3
"""Export country-profile datasets (D5–D8) for the Observable Framework site.

Spec: docs/SITE_SPECS.md §4.2, §5.2 (contracts) and §10 (performance budget).
Source logic mirrors country_trade_profile.ipynb §1–§3, with two deliberate
refinements (documented in the per-country meta.json):

* mirror totals always sum the individual partner reports (verified live:
  the API returns no 'World' reporter row for reporter=all, and reporter=0
  returns empty) — the World row is never mixed into an aggregate, so the
  double counting a naive sum would risk cannot occur;
* partner/product names are emitted in Portuguese (curated dictionary with
  English fallback), matching the site's language.

Runs locally from the repo venv; reuses the comtradetools cache (cache/) and the
API key (config.ini). Fully resumable: re-running skips API chunks already in
cache, so after an interrupt just run the same command again.

Usage (from the repo root):
    venv/bin/python site/scripts/export_profiles.py                 # all 9 PLPs
    venv/bin/python site/scripts/export_profiles.py --countries angola brasil
    venv/bin/python site/scripts/export_profiles.py --end 2024

Query plan (per docs/SITE_SPECS.md §5.2, D5–D8):
    Q1/Q2  reporter=<9 PLPs>, partner=all, flow X/M, TOTAL   -> D5-direct + D6-direct
    Q3/Q4  reporter=all, partner=<9 PLPs>, flow M/X, TOTAL   -> D5-mirror + D6-mirror
    D7d    reporter=C, partner=World, flow X/M, AG6          -> direct top products
    D7m    strong direct reporters: derived from the D8 mirror frame;
           weak direct reporters: full reporter=all AG6 fetch (small there)
    D8     reporter=C partner=all / reporter=all partner=C, restricted to the
           all-time top HS6 codes via cmdCode CSV lists      -> product x partner

Mirror-side convention (verified live 2026-07-19): reporter=all responses
carry NO 'World' reporter row and reporterCode='0' returns empty, so mirror
totals and share bases always sum the individual reporters; the World row is
never mixed in (the notebook's blanket sum would double count if it were).
Direct-side product totals use the partnerCode=0 (World) rows of the
country's own AG6 report.

Large AG6 responses: fetch_guarded sanity-checks every result against the
per-call API record cap and refetches year by year only when suspicious —
period splitting and caching stay inside comtradetools.getFinalData.
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

# Profiled countries: slug -> (M49 code, Portuguese name). The slug is used in
# filenames and in /perfis/<slug> routes.
COUNTRIES = {
    "angola": (24, "Angola"),
    "brasil": (76, "Brasil"),
    "cabo-verde": (132, "Cabo Verde"),
    "guine-bissau": (624, "Guiné-Bissau"),
    "guine-equatorial": (226, "Guiné Equatorial"),
    "mocambique": (508, "Moçambique"),
    "portugal": (620, "Portugal"),
    "sao-tome-e-principe": (678, "São Tomé e Príncipe"),
    "timor-leste": (626, "Timor-Leste"),
}

SOURCE_NOTEBOOK = "country_trade_profile.ipynb"
TOP_N = 10            # rows kept per (year, basis) in D6/D7 (spec §10)
D8_COVERAGE = 25      # all-time top products whose product×partner detail is fetched
D8_PARTNERS = 8       # partners kept per (year, hs6, basis) in D8
STRONG_YEARS = 15     # direct AG6 covering >= this many years = "strong reporter"
ROW_CAP = 99_000  # a single API call near the record cap is probably truncated

# Portuguese names for frequent trade partners, keyed by Comtrade English
# reporter/partner names. Resolved to M49 codes via comtradetools at runtime;
# unknown partners fall back to their Comtrade English name.
# NOTE: keep the project's naming for China's special regions.
PARTNERS_EN2PT = {
    "China": "China",
    "China, Macao SAR": "Macau (RAEM)",
    "China, Hong Kong SAR": "Hong Kong (RAEHK)",
    "Other Asia, nes": "Taiwan (Prov. China)",
    "USA": "EUA",
    "Germany": "Alemanha",
    "Spain": "Espanha",
    "France": "França",
    "Italy": "Itália",
    "Netherlands": "Países Baixos",
    "United Kingdom": "Reino Unido",
    "Belgium": "Bélgica",
    "Switzerland": "Suíça",
    "Sweden": "Suécia",
    "Norway": "Noruega",
    "Denmark": "Dinamarca",
    "Finland": "Finlândia",
    "Poland": "Polónia",
    "Austria": "Áustria",
    "Ireland": "Irlanda",
    "Greece": "Grécia",
    "Portugal": "Portugal",
    "Türkiye": "Turquia",
    "Russian Federation": "Rússia",
    "Ukraine": "Ucrânia",
    "India": "Índia",
    "Japan": "Japão",
    "Rep. of Korea": "Coreia do Sul",
    "Dem. People's Rep. of Korea": "Coreia do Norte",
    "Singapore": "Singapura",
    "Thailand": "Tailândia",
    "Viet Nam": "Vietname",
    "Indonesia": "Indonésia",
    "Malaysia": "Malásia",
    "Philippines": "Filipinas",
    "Australia": "Austrália",
    "New Zealand": "Nova Zelândia",
    "Canada": "Canadá",
    "Mexico": "México",
    "Argentina": "Argentina",
    "Chile": "Chile",
    "Colombia": "Colômbia",
    "Peru": "Peru",
    "Uruguay": "Uruguai",
    "Paraguay": "Paraguai",
    "Brazil": "Brasil",
    "South Africa": "África do Sul",
    "Nigeria": "Nigéria",
    "Egypt": "Egito",
    "Morocco": "Marrocos",
    "Algeria": "Argélia",
    "Saudi Arabia": "Arábia Saudita",
    "United Arab Emirates": "Emirados Árabes Unidos",
    "Qatar": "Catar",
    "Kuwait": "Kuwait",
    "Iraq": "Iraque",
    "Iran": "Irão",
    "Israel": "Israel",
    "Bangladesh": "Bangladesh",
    "Pakistan": "Paquistão",
    "Sri Lanka": "Sri Lanka",
    "Cameroon": "Camarões",
    "Bulgaria": "Bulgária",
    "Estonia": "Estónia",
    "Latvia": "Letónia",
    "Lithuania": "Lituânia",
    "Romania": "Roménia",
    "Hungary": "Hungria",
    "Slovakia": "Eslováquia",
    "Slovenia": "Eslovénia",
    "Croatia": "Croácia",
    "Serbia": "Sérvia",
    "Czechia": "Chéquia",
    "Luxembourg": "Luxemburgo",
    "Iceland": "Islândia",
    "Malta": "Malta",
    "Cyprus": "Chipre",
    "Belarus": "Bielorrússia",
    "Kazakhstan": "Cazaquistão",
    "Ghana": "Gana",
    "Côte d'Ivoire": "Costa do Marfim",
    "Kenya": "Quénia",
    "United Rep. of Tanzania": "Tanzânia",
    "Dem. Rep. of the Congo": "RD Congo",
    "Congo": "Congo",
    "Senegal": "Senegal",
    "Benin": "Benim",
    "Togo": "Togo",
    "Gabon": "Gabão",
    "Namibia": "Namíbia",
    "Botswana": "Botsuana",
    "Zambia": "Zâmbia",
    "Zimbabwe": "Zimbabué",
    "Ethiopia": "Etiópia",
    "Uganda": "Uganda",
    "Mauritania": "Mauritânia",
    "Mauritius": "Maurícias",
    "Comoros": "Comores",
    "Madagascar": "Madagáscar",
    "Dominican Rep.": "República Dominicana",
    "Cuba": "Cuba",
    "Venezuela": "Venezuela",
    "Bolivia (Plurinational State of)": "Bolívia",
    "Ecuador": "Equador",
    "Guatemala": "Guatemala",
    "Honduras": "Honduras",
    "Costa Rica": "Costa Rica",
    "Panama": "Panamá",
    "Oman": "Omã",
    "Bahrain": "Barém",
    "Jordan": "Jordânia",
    "Lebanon": "Líbano",
    "Angola": "Angola",
    "Cabo Verde": "Cabo Verde",
    "Guinea-Bissau": "Guiné-Bissau",
    "Equatorial Guinea": "Guiné Equatorial",
    "Mozambique": "Moçambique",
    "Sao Tome and Principe": "São Tomé e Príncipe",
    "Timor-Leste": "Timor-Leste",
}

# Portuguese labels for HS6 products frequent in PLP trade; other codes fall
# back to the English HS description from comtradetools.HS_CODES.
HS_PT = {
    "0302": "Peixe fresco ou refrigerado",
    "0303": "Peixe congelado",
    "0304": "Filetes de peixe",
    "0306": "Crustáceos",
    "0307": "Moluscos",
    "0801": "Cocos, castanhas de caju e nozes",
    "0901": "Café",
    "0902": "Chá",
    "1006": "Arroz",
    "1201": "Soja",
    "1507": "Óleo de soja",
    "1511": "Óleo de palma",
    "1701": "Açúcar de cana ou de beterraba",
    "1801": "Cacau",
    "2203": "Cerveja",
    "2204": "Vinho",
    "2401": "Tabaco não manufaturado",
    "2402": "Cigarros",
    "2501": "Sal",
    "2601": "Minério de ferro",
    "2603": "Minério de cobre",
    "2709": "Petróleo bruto",
    "2710": "Combustíveis refinados",
    "2711": "Gás natural e outros gases de petróleo",
    "2713": "Coque de petróleo e betume",
    "3004": "Medicamentos",
    "3901": "Polímeros de etileno",
    "4403": "Madeira em bruto",
    "4407": "Madeira serrada",
    "5201": "Algodão em fibra",
    "7102": "Diamantes",
    "7108": "Ouro",
    "7403": "Cobre refinado",
    "7601": "Alumínio em bruto",
    "8703": "Automóveis de passageiros",
    "8704": "Veículos de mercadorias",
    "8901": "Navios",
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("export_profiles")


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


def build_partner_names_pt(ctt) -> dict:
    """M49 code -> Portuguese partner name (curated dict, English fallback)."""
    code2pt = {}
    for en, pt in PARTNERS_EN2PT.items():
        code = ctt.encode_country(en)
        if isinstance(code, int):
            code2pt[code] = pt
        else:
            log.warning("PT partner mapping: could not encode '%s'", en)
    return code2pt


def partner_pt(code: int, code2pt: dict, ctt) -> str:
    if code in code2pt:
        return code2pt[code]
    name = ctt.decode_country(code)
    return name if isinstance(name, str) else str(code)


def hs_label_pt(ctt, code: str) -> str:
    """PT label for an HS6 code: exact curated match, else the curated 4-digit
    heading label, else the English HS description."""
    if code in HS_PT:
        return HS_PT[code]
    if code[:4] in HS_PT:
        return HS_PT[code[:4]]
    en = ctt.HS_CODES.get(code)
    return en if isinstance(en, str) else code


def fetch(ctt, label: str, period: str, period_size: int = 12, **kw) -> pd.DataFrame:
    """getFinalData with logging; returns empty DataFrame (never None)."""
    log.info("getFinalData %s (%s…)", label, period[:18])
    df = ctt.getFinalData(
        ctt.APIKEY,
        typeCode="C",
        freqCode="A",
        partner2Code=0,
        period=period,
        period_size=period_size,
        retry_if_empty=False,
        motCode=0,
        customsCode="C00",
        clCode="HS",
        includeDesc=False,
        **kw,
    )
    if df is None or df.empty:
        return pd.DataFrame()
    return df


def fetch_guarded(ctt, label: str, period: str, **kw) -> pd.DataFrame:
    """fetch() + record-cap guard for the (rare) potentially-large queries.

    getFinalData splits the period into <=12-period calls itself; the API
    record cap applies PER CALL, so only a total within ROW_CAP of the
    theoretical maximum (chunks x cap) can hide a truncated chunk. Anything
    smaller is complete by construction. Above it, refetch year by year
    (single-period calls can never hit the cap for these datasets).
    """
    df = fetch(ctt, label, period, **kw)
    n_periods = len(period.split(","))
    n_chunks = -(-n_periods // 12)  # ceil
    if len(df) < n_chunks * ROW_CAP:
        return df
    log.warning("%s returned %d rows (>= %d chunks x %d) — possible per-call "
                "truncation, refetching year by year",
                label, len(df), n_chunks, ROW_CAP)
    yearly = [fetch(ctt, f"{label} [{y}]", y, **kw) for y in period.split(",")]
    yearly = [d for d in yearly if not d.empty]
    return pd.concat(yearly, ignore_index=True) if yearly else pd.DataFrame()


def fetch_shared_totals(ctt, start: int, end: int) -> dict:
    """Q1–Q4: TOTAL flows for all 9 PLPs at once (direct and mirror sides)."""
    period = year_list(start, end)
    plp9 = ",".join(str(code) for code, _ in COUNTRIES.values())
    return {
        "x_direct": fetch(ctt, "Q1 reporter=PLP9 partner=all X TOTAL", period,
                          reporterCode=plp9, partnerCode=None, flowCode="X",
                          cmdCode="TOTAL"),
        "m_direct": fetch(ctt, "Q2 reporter=PLP9 partner=all M TOTAL", period,
                          reporterCode=plp9, partnerCode=None, flowCode="M",
                          cmdCode="TOTAL"),
        "x_mirror": fetch(ctt, "Q3 reporter=all partner=PLP9 M TOTAL", period,
                          reporterCode=None, partnerCode=plp9, flowCode="M",
                          cmdCode="TOTAL"),
        "m_mirror": fetch(ctt, "Q4 reporter=all partner=PLP9 X TOTAL", period,
                          reporterCode=None, partnerCode=plp9, flowCode="X",
                          cmdCode="TOTAL"),
    }


def world_total(df: pd.DataFrame, country_code: int, side: str) -> pd.DataFrame:
    """(year, total) series for a country from a shared TOTAL query.

    side='direct': rows reporterCode=country & partnerCode=0 (World row).
    side='mirror': rows partnerCode=country summed over reporters != 0
    (reporter=all responses carry no 'World' reporter row — verified
    2026-07-19 against cached Q3/Q4 chunks).
    """
    if df.empty:
        return pd.DataFrame(columns=["year", "total"])
    if side == "direct":
        sel = df[(df["reporterCode"] == country_code) & (df["partnerCode"] == 0)]
        g = sel.groupby("period")["primaryValue"].sum()
    else:
        sel = df[(df["partnerCode"] == country_code) & (df["reporterCode"] != 0)]
        g = sel.groupby("period")["primaryValue"].sum()
    out = g.reset_index().rename(columns={"period": "year", "primaryValue": "total"})
    out["year"] = out["year"].astype(int)
    return out


def build_d5(shared: dict, country_code: int, start: int, end: int) -> pd.DataFrame:
    """D5 trade balance, long format: year, basis, exports, imports, volume, balance."""
    xd = world_total(shared["x_direct"], country_code, "direct").set_index("year")["total"]
    md = world_total(shared["m_direct"], country_code, "direct").set_index("year")["total"]
    xm = world_total(shared["x_mirror"], country_code, "mirror").set_index("year")["total"]
    mm = world_total(shared["m_mirror"], country_code, "mirror").set_index("year")["total"]
    rows = []
    for year in range(start, end + 1):
        for basis, x, m in (("direct", xd, md), ("mirror", xm, mm)):
            e, i = int(x.get(year, 0)), int(m.get(year, 0))
            rows.append(dict(year=year, basis=basis, exports=e, imports=i,
                             trade_volume=e + i, balance=e - i))
    return pd.DataFrame(rows).sort_values(["year", "basis"]).reset_index(drop=True)


def build_d6(shared: dict, country_code: int, code2pt: dict, ctt,
             direction: str) -> pd.DataFrame:
    """D6 top partners (top-N per year/basis) for 'exports' or 'imports'.

    Direct: partner rows (partnerCode != 0) of the country's own X/M report;
    share vs the World (partnerCode=0) row. Mirror: reporter rows
    (reporterCode != 0) reporting M/X with the country as partner; share vs
    the sum over reporters (World reporter row excluded).
    """
    df = shared["x_direct" if direction == "exports" else "m_direct"]
    df_m = shared["x_mirror" if direction == "exports" else "m_mirror"]
    rows = []

    def emit(sub: pd.DataFrame, code_col: str, totals: pd.Series, basis: str):
        if sub.empty:
            return
        for year, grp in sub.groupby("period"):
            year = int(year)
            grp = grp.sort_values("primaryValue", ascending=False).head(TOP_N)
            total = totals.get(year, 0)
            for rank, (_, r) in enumerate(grp.iterrows(), start=1):
                code = int(r[code_col])
                rows.append(dict(
                    year=int(year), partner_code=code,
                    partner=partner_pt(code, code2pt, ctt),
                    value=int(round(r["primaryValue"])),
                    share_pct=round(r["primaryValue"] / total * 100, 3) if total else None,
                    rank=rank, basis=basis))

    d = df[(df["reporterCode"] == country_code) & (df["partnerCode"] != 0)]
    emit(d, "partnerCode",
         world_total(df, country_code, "direct").set_index("year")["total"], "direct")
    m = df_m[(df_m["partnerCode"] == country_code) & (df_m["reporterCode"] != 0)]
    emit(m, "reporterCode",
         world_total(df_m, country_code, "mirror").set_index("year")["total"], "mirror")

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out = out.dropna(subset=["share_pct"])  # years with no reported total
    out["share_pct"] = out["share_pct"].astype(float)
    return out.sort_values(["year", "basis", "rank"]).reset_index(drop=True)


def fetch_d7_direct_frames(ctt, slug: str, country_code: int, start: int,
                           end: int) -> dict:
    """D7 direct discovery — the country's own report with partner=World
    (partnerCode=0), AG6. Small responses, no truncation risk."""
    period = year_list(start, end)
    return {
        "x": fetch_guarded(ctt, f"{slug} D7d reporter=C partner=World X AG6",
                           period, reporterCode=str(country_code),
                           partnerCode="0", flowCode="X", cmdCode="AG6"),
        "m": fetch_guarded(ctt, f"{slug} D7d reporter=C partner=World M AG6",
                           period, reporterCode=str(country_code),
                           partnerCode="0", flowCode="M", cmdCode="AG6"),
    }


def fetch_d7_mirror_full(ctt, slug: str, country_code: int, start: int,
                         end: int) -> dict:
    """D7 mirror discovery via a FULL reporter=all AG6 fetch (fallback for
    countries with weak direct reporting — their mirror trade is small).
    NOTE: reporter=all responses carry no 'World' reporter row (verified
    2026-07-19 against cached chunks) and reporterCode='0' returns empty,
    so summing individual reporters is the only mirror aggregate available."""
    period = year_list(start, end)
    return {
        "x": fetch_guarded(ctt, f"{slug} D7m reporter=all partner=C M AG6 (full)",
                           period, reporterCode=None, partnerCode=str(country_code),
                           flowCode="M", cmdCode="AG6"),
        "m": fetch_guarded(ctt, f"{slug} D7m reporter=all partner=C X AG6 (full)",
                           period, reporterCode=None, partnerCode=str(country_code),
                           flowCode="X", cmdCode="AG6"),
    }


def product_totals_from_d8(df: pd.DataFrame, side: str) -> pd.DataFrame:
    """(year, hs6, value) mirror product totals from a D8 frame (top-code
    restricted): sum over partner rows (reporterCode != 0)."""
    cols = ["year", "hs6", "value"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    sel = df[df["reporterCode"] != 0] if side == "mirror" else df[df["partnerCode"] != 0]
    if sel.empty:
        return pd.DataFrame(columns=cols)
    g = (sel.groupby(["period", "cmdCode"])["primaryValue"].sum().reset_index()
         .rename(columns={"period": "year", "cmdCode": "hs6", "primaryValue": "value"}))
    g["year"] = g["year"].astype(int)
    g["hs6"] = g["hs6"].astype(str)
    return g[g["value"] > 0].reset_index(drop=True)


def fetch_d8_frames(ctt, slug: str, country_code: int, direction: str,
                    top_codes: set, start: int, end: int) -> dict:
    """D8 product×partner detail, restricted to the top HS6 codes (small).

    direct: reporter=C, partner=all; mirror: reporter=all, partner=C.
    Kept to <= 2 x TOP_PRODUCTS codes per direction, so responses stay far
    below the API record cap (fetch_guarded still checks the result).
    """
    if not top_codes:
        return {"direct": pd.DataFrame(), "mirror": pd.DataFrame()}
    period = year_list(start, end)
    codes = ",".join(sorted(top_codes))
    if direction == "exports":   # direct: country reports X; mirror: partners report M
        direct_flow, mirror_flow = "X", "M"
    else:
        direct_flow, mirror_flow = "M", "X"
    return {
        "direct": fetch_guarded(
            ctt, f"{slug} D8d {direction} reporter=C partner=all AG6[{len(top_codes)}]",
            period, reporterCode=str(country_code), partnerCode=None,
            flowCode=direct_flow, cmdCode=codes),
        "mirror": fetch_guarded(
            ctt, f"{slug} D8m {direction} reporter=all partner=C AG6[{len(top_codes)}]",
            period, reporterCode=None, partnerCode=str(country_code),
            flowCode=mirror_flow, cmdCode=codes),
    }


def product_totals(df: pd.DataFrame) -> pd.DataFrame:
    """(year, hs6, value) world-level product totals from a D7 frame.

    D7 frames are already world-level (partner=World rows for direct; World
    reporter rows, or the fallback's reporters != 0, for mirror).
    """
    cols = ["year", "hs6", "value"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    g = (df.groupby(["period", "cmdCode"])["primaryValue"].sum().reset_index()
         .rename(columns={"period": "year", "cmdCode": "hs6", "primaryValue": "value"}))
    g["year"] = g["year"].astype(int)
    g["hs6"] = g["hs6"].astype(str)
    return g[g["value"] > 0].reset_index(drop=True)


def build_d7(prod: pd.DataFrame, world_totals: pd.Series, ctt) -> pd.DataFrame:
    """D7 top products (top-N per year/basis) from a product_totals frame."""
    rows = []
    for year, grp in prod.groupby("year"):
        grp = grp.sort_values("value", ascending=False).head(TOP_N)
        total = world_totals.get(year, 0)
        if not total:
            continue  # no reported total that year -> share would be NaN
        for rank, (_, r) in enumerate(grp.iterrows(), start=1):
            rows.append(dict(year=int(year), hs6=str(r["hs6"]),
                             description_pt=hs_label_pt(ctt, str(r["hs6"])),
                             value=int(round(r["value"])),
                             share_pct=round(r["value"] / total * 100, 3),
                             rank=rank))
    return pd.DataFrame(rows)


def top_products_alltime(prod_frames: list, n: int) -> set:
    """Union of the all-time top-N HS6 codes across the given product frames."""
    frames = [f for f in prod_frames if not f.empty]
    if not frames:
        return set()
    alltime = (pd.concat(frames).groupby("hs6")["value"].sum()
               .sort_values(ascending=False).head(n))
    return set(alltime.index)


def build_d8(df: pd.DataFrame, side: str, code2pt: dict, ctt) -> pd.DataFrame:
    """D8 product×partner detail from a D8 frame (already top-HS6-restricted).

    Keeps the top-D8_PARTNERS partners per (year, hs6). share_pct is the
    partner's share of the product-year total: the World rows of the same
    frame when present (partnerCode=0 direct / reporterCode=0 mirror), else
    the sum over partners.
    """
    if df.empty:
        return pd.DataFrame()
    if side == "direct":
        partners = df[(df["partnerCode"] != 0) & (df["primaryValue"] > 0)].copy()
        partners["partner_code"] = partners["partnerCode"]
        world = df[df["partnerCode"] == 0]
    else:
        partners = df[(df["reporterCode"] != 0) & (df["primaryValue"] > 0)].copy()
        partners["partner_code"] = partners["reporterCode"]
        world = df[df["reporterCode"] == 0]
    if partners.empty:
        return pd.DataFrame()
    base = world if not world.empty else partners
    totals = (base.groupby(["period", "cmdCode"])["primaryValue"].sum().reset_index())
    totals["period"] = totals["period"].astype(int)
    totals["cmdCode"] = totals["cmdCode"].astype(str)
    totals = totals.set_index(["period", "cmdCode"])["primaryValue"]
    rows = []
    for (year, hs6), grp in partners.groupby(["period", "cmdCode"]):
        year, hs6 = int(year), str(hs6)
        grp = grp.sort_values("primaryValue", ascending=False).head(D8_PARTNERS)
        total = totals.get((year, hs6), 0)
        if not total:
            continue
        for _, r in grp.iterrows():
            value = int(round(r["primaryValue"]))
            if value <= 0:
                continue  # sub-USD fractional rows round to zero — drop
            code = int(r["partner_code"])
            rows.append(dict(year=int(year), hs6=str(hs6),
                             description_pt=hs_label_pt(ctt, str(hs6)),
                             partner_code=code,
                             partner=partner_pt(code, code2pt, ctt),
                             value=value,
                             share_pct=round(r["primaryValue"] / total * 100, 3)))
    out = pd.DataFrame(rows)
    return out.sort_values(["year", "hs6", "value"],
                           ascending=[True, True, False]).reset_index(drop=True)


D5_COLS = ["year", "basis", "exports", "imports", "trade_volume", "balance"]
D6_COLS = ["year", "partner_code", "partner", "value", "share_pct", "rank", "basis"]
D7_COLS = ["year", "hs6", "description_pt", "value", "share_pct", "rank", "basis"]
D8_COLS = ["year", "hs6", "description_pt", "partner_code", "partner", "value",
           "share_pct", "basis"]


def write_csv(df: pd.DataFrame, stem: str, cols: list) -> tuple:
    path = OUT_DIR / f"{stem}.csv"
    if df.empty:
        df = pd.DataFrame(columns=cols)
    df = df[cols]
    df.to_csv(path, index=False)
    log.info("wrote %s (%d rows)", path.name, len(df))
    return path, len(df)


def export_country(ctt, slug: str, shared: dict, code2pt: dict,
                   start: int, end: int) -> bool:
    country_code, name_pt = COUNTRIES[slug]
    log.info("=== %s (%s) ===", name_pt, slug)

    # D5 and D6 come from the shared TOTAL queries (already fetched).
    d5 = build_d5(shared, country_code, start, end)
    d6x = build_d6(shared, country_code, code2pt, ctt, "exports")
    d6m = build_d6(shared, country_code, code2pt, ctt, "imports")

    # D7 direct discovery (world-level, small responses).
    d7d = fetch_d7_direct_frames(ctt, slug, country_code, start, end)
    prod_xd = product_totals(d7d["x"])
    prod_md = product_totals(d7d["m"])
    strong_x = not prod_xd.empty and prod_xd["year"].nunique() >= STRONG_YEARS
    strong_m = not prod_md.empty and prod_md["year"].nunique() >= STRONG_YEARS

    if strong_x and strong_m:
        # Strong direct reporter: mirror product views are derived from the
        # D8 frames (restricted to the direct all-time top-D8_COVERAGE codes),
        # avoiding two full-detail mirror AG6 fetches.
        keep_x = top_products_alltime([prod_xd], D8_COVERAGE)
        keep_m = top_products_alltime([prod_md], D8_COVERAGE)
        d8fx = fetch_d8_frames(ctt, slug, country_code, "exports", keep_x, start, end)
        d8fm = fetch_d8_frames(ctt, slug, country_code, "imports", keep_m, start, end)
        prod_xm = product_totals_from_d8(d8fx["mirror"], "mirror")
        prod_mm = product_totals_from_d8(d8fm["mirror"], "mirror")
        mirror_scope = (f"mirror product views (D7-mirror, D8-mirror) cover the "
                        f"country's all-time top-{D8_COVERAGE} direct products; "
                        f"products outside that set are not shown on the mirror basis")
    else:
        # Weak direct reporter (e.g. long non-reporting gaps): the mirror side
        # is the primary view, so discover top products from a full mirror AG6
        # fetch (small for these countries; per-chunk cap guard still applies).
        log.warning("%s: weak direct AG6 reporting (X: %d years, M: %d years) — "
                    "using full mirror AG6 for top-product discovery", slug,
                    prod_xd["year"].nunique(), prod_md["year"].nunique())
        d7mf = fetch_d7_mirror_full(ctt, slug, country_code, start, end)
        prod_xm = product_totals(d7mf["x"])
        prod_mm = product_totals(d7mf["m"])
        keep_x = top_products_alltime([prod_xd, prod_xm], D8_COVERAGE)
        keep_m = top_products_alltime([prod_md, prod_mm], D8_COVERAGE)
        d8fx = fetch_d8_frames(ctt, slug, country_code, "exports", keep_x, start, end)
        d8fm = fetch_d8_frames(ctt, slug, country_code, "imports", keep_m, start, end)
        mirror_scope = None

    tot_xd = world_total(shared["x_direct"], country_code, "direct").set_index("year")["total"]
    tot_md = world_total(shared["m_direct"], country_code, "direct").set_index("year")["total"]
    tot_xm = world_total(shared["x_mirror"], country_code, "mirror").set_index("year")["total"]
    tot_mm = world_total(shared["m_mirror"], country_code, "mirror").set_index("year")["total"]

    d7x = pd.concat([build_d7(prod_xd, tot_xd, ctt).assign(basis="direct"),
                     build_d7(prod_xm, tot_xm, ctt).assign(basis="mirror")],
                    ignore_index=True)
    d7m_ = pd.concat([build_d7(prod_md, tot_md, ctt).assign(basis="direct"),
                      build_d7(prod_mm, tot_mm, ctt).assign(basis="mirror")],
                     ignore_index=True)
    if not d7x.empty:
        d7x = d7x.sort_values(["year", "basis", "rank"]).reset_index(drop=True)
    if not d7m_.empty:
        d7m_ = d7m_.sort_values(["year", "basis", "rank"]).reset_index(drop=True)

    # D8: product×partner rows come from the D8 frames fetched above.
    d8x = pd.concat([
        build_d8(d8fx["direct"], "direct", code2pt, ctt).assign(basis="direct"),
        build_d8(d8fx["mirror"], "mirror", code2pt, ctt).assign(basis="mirror")],
        ignore_index=True)
    d8m = pd.concat([
        build_d8(d8fm["direct"], "direct", code2pt, ctt).assign(basis="direct"),
        build_d8(d8fm["mirror"], "mirror", code2pt, ctt).assign(basis="mirror")],
        ignore_index=True)
    if not d8x.empty:
        d8x = d8x.sort_values(["year", "basis", "hs6", "value"],
                              ascending=[True, True, True, False]).reset_index(drop=True)
    if not d8m.empty:
        d8m = d8m.sort_values(["year", "basis", "hs6", "value"],
                              ascending=[True, True, True, False]).reset_index(drop=True)

    span = f"{start}-{end}"
    stem = lambda s: f"{slug}_{s}_{span}"  # noqa: E731
    files = {}
    files["trade_balance"], n5 = write_csv(d5, stem("trade_balance"), D5_COLS)
    files["top_partners_exports"], n6x = write_csv(d6x, stem("top_partners_exports"), D6_COLS)
    files["top_partners_imports"], n6m = write_csv(d6m, stem("top_partners_imports"), D6_COLS)
    files["top_products_exports_HS-AG6"], n7x = write_csv(
        d7x, stem("top_products_exports_HS-AG6"), D7_COLS)
    files["top_products_imports_HS-AG6"], n7m = write_csv(
        d7m_, stem("top_products_imports_HS-AG6"), D7_COLS)
    files["products_partners_HS-AG6"], n8x = write_csv(
        d8x, stem("products_partners_HS-AG6"), D8_COLS)
    files["partners_products_HS-AG6"], n8m = write_csv(
        d8m, stem("partners_products_HS-AG6"), D8_COLS)

    if n5 == 0 or (n6x == 0 and n6m == 0) or (n7x == 0 and n7m == 0):
        log.error("%s: suspiciously empty datasets (D5=%d, D6=%d/%d, D7=%d/%d) — "
                  "check API/cache before committing", slug, n5, n6x, n6m, n7x, n7m)
        return False

    meta = {
        "dataset": f"{slug}_profile",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_notebook": SOURCE_NOTEBOOK,
        "country_code": country_code,
        "country_name_pt": name_pt,
        "units": "USD (current)",
        "flow_basis": "both — 'direct' (reported by the country) and 'mirror' "
                      "(reported by its partners; mirror totals sum the "
                      "individual reporters — reporter=all responses carry no "
                      "'World' reporter row, and reporter=0 returns no data)",
        "period": span,
        "files": {k: {"file": v.name, "rows": n}
                  for (k, v), n in zip(files.items(),
                                       [n5, n6x, n6m, n7x, n7m, n8x, n8m])},
        "notes": "From the country's own perspective: exports = country -> "
                 "partner. D6/D7 keep top-10 per (year, basis); D8 keeps "
                 f"all-time top-{D8_COVERAGE} products x top-{D8_PARTNERS} "
                 "partners per (year, hs6, basis). share_pct of D6/D7 uses "
                 "the year's world total of the same basis; D8 share_pct uses "
                 "the product-year total. description_pt: curated PT label "
                 "where available, else the English HS description. An "
                 "unreported flow/year contributes 0 (see export_site_data.py "
                 "notes)." + (f" NOTE: {mirror_scope}." if mirror_scope else ""),
    }
    meta_path = OUT_DIR / f"{slug}_profile_{span}.meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    log.info("wrote %s", meta_path.name)
    return True


def write_hs_labels(ctt):
    """Reference file: PT/EN labels for every HS6 code used in D7/D8 CSVs."""
    codes = set()
    for pattern in ("*_top_products_*_HS-AG6_*.csv", "*_products_partners_HS-AG6_*.csv",
                    "*_partners_products_HS-AG6_*.csv"):
        for csv in OUT_DIR.glob(pattern):
            if csv.name.startswith(("cn_", "mo_", "hk_")):
                continue
            try:
                codes.update(pd.read_csv(csv, usecols=["hs6"], dtype=str)["hs6"].unique())
            except (ValueError, pd.errors.EmptyDataError):
                continue  # csv without hs6 data
    rows = []
    missing_en = 0
    for code in sorted(codes):
        en = ctt.HS_CODES.get(code)
        if not isinstance(en, str):
            en, missing_en = code, missing_en + 1
        rows.append({"hs6": code, "en": en,
                     "pt": HS_PT.get(code, HS_PT.get(code[:4]))})
    path = OUT_DIR / "hs_ag6_labels.json"
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    log.info("wrote %s (%d codes, %d without EN HS label)", path.name, len(rows), missing_en)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--countries", nargs="+", choices=COUNTRIES.keys(),
                    default=list(COUNTRIES.keys()),
                    help="country slugs to export (default: all 9)")
    ap.add_argument("--start", type=int, default=2003)
    ap.add_argument("--end", type=int, default=2024,
                    help="default 2024: consistent with the flows snapshots and "
                         "the validated Forum quadros")
    args = ap.parse_args()

    ctt = init_comtradetools()
    code2pt = build_partner_names_pt(ctt)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    shared = fetch_shared_totals(ctt, args.start, args.end)
    if shared["x_direct"].empty and shared["x_mirror"].empty:
        log.error("shared TOTAL queries came back empty — aborting "
                      "(guard against partial API data)")
        sys.exit(1)

    ok = True
    for slug in args.countries:
        ok = export_country(ctt, slug, shared, code2pt, args.start, args.end) and ok

    write_hs_labels(ctt)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
