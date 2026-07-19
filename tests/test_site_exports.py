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
