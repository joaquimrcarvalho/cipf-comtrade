"""Offline schema tests for the committed site data snapshots.

Spec: docs/SITE_SPECS.md §5.2 (contracts) and §9.3 (schema tests).
These tests validate files committed under site/src/data/; they do not touch
the network or comtradetools. Regenerate snapshots with:
    venv/bin/python site/scripts/export_site_data.py --check
"""

import json
from pathlib import Path

import pandas as pd
import pytest

DATA_DIR = Path(__file__).resolve().parents[1] / "site" / "src" / "data"

FLOWS_COLS = ["year", "partner_code", "partner", "exports", "imports",
              "trade_volume", "balance", "basis"]
PLP_CODES = {24, 76, 132, 226, 508, 620, 624, 626, 678}
META_REQUIRED = {"dataset", "generated_at", "source_notebook", "reporter_code",
                 "reporter_name", "units", "flow_basis", "period", "rows"}


def flows_csvs():
    return sorted(DATA_DIR.glob("*_plp_flows_*.csv"))


def test_flows_snapshots_exist():
    assert flows_csvs(), f"no *_plp_flows_*.csv under {DATA_DIR} — run the export script"


@pytest.mark.parametrize("csv_path", flows_csvs() or [None])
def test_flows_schema(csv_path):
    if csv_path is None:
        pytest.skip("no snapshots present")
    df = pd.read_csv(csv_path)

    # columns, order and completeness
    assert list(df.columns) == FLOWS_COLS
    assert not df.isna().any().any(), "snapshot must not contain NaN"

    # domains
    assert set(df["basis"].unique()) <= {"direct", "mirror"}
    assert set(df["partner_code"].unique()) <= PLP_CODES
    assert df["year"].between(2003, 2100).all()
    assert (df[["exports", "imports", "trade_volume"]] >= 0).all().all()

    # internal consistency
    assert (df["trade_volume"] == df["exports"] + df["imports"]).all()
    assert (df["balance"] == df["exports"] - df["imports"]).all()

    # granularity: unique (year, partner, basis); reasonable coverage
    assert not df.duplicated(subset=["year", "partner_code", "basis"]).any()
    assert df["partner_code"].nunique() >= 5
    assert df["year"].nunique() >= 10

    # deterministic ordering
    ordered = df.sort_values(["year", "partner_code", "basis"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(df.reset_index(drop=True), ordered)


@pytest.mark.parametrize("csv_path", flows_csvs() or [None])
def test_flows_meta(csv_path):
    if csv_path is None:
        pytest.skip("no snapshots present")
    meta_path = csv_path.with_suffix(".meta.json")
    assert meta_path.exists(), f"missing {meta_path.name}"
    meta = json.loads(meta_path.read_text())
    assert META_REQUIRED <= set(meta), f"missing keys: {META_REQUIRED - set(meta)}"
    assert meta["units"] == "USD (current)"
    assert meta["rows"] == len(pd.read_csv(csv_path))


def test_plp_countries_reference():
    path = DATA_DIR / "plp_countries.json"
    assert path.exists(), "missing plp_countries.json — run the export script"
    rows = json.loads(path.read_text())
    assert {r["code"] for r in rows} == PLP_CODES
    assert all(r["name_pt"] and r["name_en"] for r in rows)


# ---------------------------------------------------------------------------
# Country profiles (D5–D8), spec §5.2 — export_profiles.py
# ---------------------------------------------------------------------------

PROFILE_SLUGS = {
    "angola": 24, "brasil": 76, "cabo-verde": 132, "guine-bissau": 624,
    "guine-equatorial": 226, "mocambique": 508, "portugal": 620,
    "sao-tome-e-principe": 678, "timor-leste": 626,
}
D5_COLS = ["year", "basis", "exports", "imports", "trade_volume", "balance"]
D6_COLS = ["year", "partner_code", "partner", "value", "share_pct", "rank", "basis"]
D7_COLS = ["year", "hs6", "description_pt", "value", "share_pct", "rank", "basis"]
D8_COLS = ["year", "hs6", "description_pt", "partner_code", "partner", "value",
           "share_pct", "basis"]
D11_COLS = ["year", "partner_code", "partner", "hs6", "description_pt",
           "competitor_code", "competitor", "value", "share_pct", "rank",
           "is_country", "market_total"]
PROFILE_META_REQUIRED = {"dataset", "generated_at", "source_notebook", "country_code",
                         "country_name_pt", "units", "flow_basis", "period", "files"}


def profile_csv(slug, kind):
    files = list(DATA_DIR.glob(f"{slug}_{kind}_*.csv"))
    return files[0] if files else None


def read_profile(slug, kind, cols):
    """Read a profile CSV, tolerating empty (header-only) files."""
    path = profile_csv(slug, kind)
    assert path is not None, f"missing {slug}_{kind}_*.csv — run export_profiles.py"
    if path.stat().st_size == 0:
        pytest.fail(f"{path.name} is a zero-byte file")
    df = pd.read_csv(path, dtype={"hs6": str})
    assert list(df.columns) == cols, f"{path.name}: {list(df.columns)} != {cols}"
    return df


@pytest.mark.parametrize("slug", sorted(PROFILE_SLUGS))
def test_d5_trade_balance(slug):
    df = read_profile(slug, "trade_balance", D5_COLS)
    assert not df.isna().any().any()
    # a basis appears only when reported (e.g. Equatorial Guinea is mirror-only)
    assert set(df["basis"].unique()) <= {"direct", "mirror"}
    assert len(df) > 0
    assert df["year"].between(2003, 2100).all()
    assert (df["trade_volume"] == df["exports"] + df["imports"]).all()
    assert (df["balance"] == df["exports"] - df["imports"]).all()
    assert not df.duplicated(subset=["year", "basis"]).any()
    # no fabricated zeros: a row exists only if that basis was reported that year
    assert not ((df["exports"] == 0) & (df["imports"] == 0)).any()
    assert df["year"].nunique() >= 20, "D5 covers the period (>=1 basis per year)"
    ordered = df.sort_values(["year", "basis"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(df.reset_index(drop=True), ordered)


@pytest.mark.parametrize("slug", sorted(PROFILE_SLUGS))
@pytest.mark.parametrize("kind", ["top_partners_exports", "top_partners_imports"])
def test_d6_top_partners(slug, kind):
    df = read_profile(slug, kind, D6_COLS)
    if df.empty:
        pytest.skip(f"{slug} {kind}: legitimately empty (no reported data)")
    assert not df.isna().any().any()
    assert set(df["basis"].unique()) <= {"direct", "mirror"}
    assert (df["value"] > 0).all()
    assert df["share_pct"].between(0, 100, inclusive="both").all()
    assert df["rank"].between(1, 10).all()
    assert (df["partner"].str.len() > 0).all()
    assert not df.duplicated(subset=["year", "basis", "rank"]).any()
    ordered = df.sort_values(["year", "basis", "rank"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(df.reset_index(drop=True), ordered)


@pytest.mark.parametrize("slug", sorted(PROFILE_SLUGS))
@pytest.mark.parametrize("kind", ["top_products_exports_HS-AG6", "top_products_imports_HS-AG6"])
def test_d7_top_products(slug, kind):
    df = read_profile(slug, kind, D7_COLS)
    if df.empty:
        pytest.skip(f"{slug} {kind}: legitimately empty (no reported data)")
    assert not df.isna().any().any()
    assert set(df["basis"].unique()) <= {"direct", "mirror"}
    assert (df["value"] > 0).all()
    assert df["share_pct"].between(0, 100, inclusive="both").all()
    assert df["rank"].between(1, 10).all()
    assert df["hs6"].str.match(r"^\d{6}$").all(), "HS-AG6 codes are 6 digits"
    assert not df.duplicated(subset=["year", "basis", "rank"]).any()
    ordered = df.sort_values(["year", "basis", "rank"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(df.reset_index(drop=True), ordered)


@pytest.mark.parametrize("slug", sorted(PROFILE_SLUGS))
@pytest.mark.parametrize("kind", ["products_partners_HS-AG6", "partners_products_HS-AG6"])
def test_d8_products_partners(slug, kind):
    df = read_profile(slug, kind, D8_COLS)
    if df.empty:
        pytest.skip(f"{slug} {kind}: legitimately empty (no reported data)")
    assert not df.isna().any().any()
    assert set(df["basis"].unique()) <= {"direct", "mirror"}
    assert (df["value"] != 0).all()
    assert df["share_pct"].abs().le(100).all()
    assert df["hs6"].str.match(r"^\d{6}$").all()
    # pre-filtered per spec §10: at most 8 partners per (year, basis, hs6)
    assert (df.groupby(["year", "basis", "hs6"]).size() <= 8).all()
    ordered = df.sort_values(["year", "basis", "hs6", "value"],
                             ascending=[True, True, True, False]).reset_index(drop=True)
    pd.testing.assert_frame_equal(df.reset_index(drop=True), ordered)


@pytest.mark.parametrize("slug", sorted(PROFILE_SLUGS))
@pytest.mark.parametrize("kind", ["competition_exports_HS-AG6",
                                  "competition_imports_HS-AG6"])
def test_d11_competition(slug, kind):
    """D11/D12 competition datasets (notebook §2.5/§3.5), spec §5.2.

    Tolerates absence during the pilot rollout: countries not yet exported
    are skipped rather than failed.
    """
    path = profile_csv(slug, kind)
    if path is None:
        pytest.skip(f"{slug} {kind}: competition dataset not exported yet")
    df = read_profile(slug, kind, D11_COLS)
    if df.empty:
        pytest.skip(f"{slug} {kind}: legitimately empty (no reported data)")
    assert not df.isna().any().any()
    assert (df["value"] > 0).all()
    assert (df["market_total"] > 0).all()
    assert df["share_pct"].between(0, 100, inclusive="both").all()
    assert (df["rank"] >= 1).all()
    assert df["hs6"].str.match(r"^\d{6}$").all()
    assert set(df["is_country"].unique()) <= {0, 1}
    # the country of interest is flagged and is never the partner
    country = PROFILE_SLUGS[slug]
    assert (df.loc[df["is_country"] == 1, "competitor_code"] == country).all()
    assert (df["partner_code"] != country).all()
    # per (year, partner, hs6): top-5 competitors + at most the country row
    assert (df.groupby(["year", "partner_code", "hs6"]).size() <= 6).all()
    # note: ranks may repeat within a market — comtradetools ranks method="dense"
    # (tied values share a rank); the exporter's row cap is what is deterministic
    ordered = df.sort_values(["year", "partner_code", "hs6", "rank"]) \
        .reset_index(drop=True)
    pd.testing.assert_frame_equal(df.reset_index(drop=True), ordered)


@pytest.mark.parametrize("slug", sorted(PROFILE_SLUGS))
def test_profile_meta(slug):
    files = list(DATA_DIR.glob(f"{slug}_profile_*.meta.json"))
    assert files, f"missing {slug}_profile_*.meta.json — run export_profiles.py"
    meta = json.loads(files[0].read_text())
    assert PROFILE_META_REQUIRED <= set(meta)
    assert meta["country_code"] == PROFILE_SLUGS[slug]
    assert meta["units"] == "USD (current)"
    assert len(meta["files"]) >= 7, "D5–D8 always present; D11/D12 added by re-export"
    for info in meta["files"].values():
        assert (DATA_DIR / info["file"]).exists(), f"missing {info['file']}"


def test_hs_labels_reference():
    path = DATA_DIR / "hs_ag6_labels.json"
    assert path.exists(), "missing hs_ag6_labels.json — run export_profiles.py"
    rows = json.loads(path.read_text())
    assert rows, "hs_ag6_labels.json is empty"
    assert all(r["hs6"] and r["en"] for r in rows)
