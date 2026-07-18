"""Pytest bootstrap: make the repo root importable and provide shared fixtures."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Support files init() needs locally (anything missing would trigger a download)
REQUIRED_SUPPORT_FILES = [
    "codebook.xlsx",
    "dataitem.csv",
    "partner.csv",
    "reporter.csv",
    "harmonized-system.csv",
    "Dim_Countries_Hierarchy_UnctadStat_All_Flat.csv",
    "COMTRADE+ COMPLETE.csv",
    "REF COUNTRIES.csv",
    "REF  MOS.csv",
    "REF CUSTOMS.csv",
    "REF FLOWS.csv",
    "REF MOT.csv",
    "REF QTY.csv",
]


@pytest.fixture(scope="session")
def ctt(tmp_path_factory):
    """Import and initialize comtradetools the way the notebooks do, but hermetically.

    Uses a throwaway config.ini (dummy key) and a throwaway cache dir so tests
    never touch the real config or the real cache. Skips if the local support
    files are absent, because init() would then need network access.
    """
    support = Path("support")
    missing = [f for f in REQUIRED_SUPPORT_FILES if not (support / f).is_file()]
    if missing:
        pytest.skip(f"support files missing, init() would need network: {missing}")

    import comtradetools

    tmp = tmp_path_factory.mktemp("ctt")
    config = tmp / "config.ini"
    config.write_text("[comtrade]\nkey = TESTKEY\n")
    cache = tmp / "cache"

    comtradetools.setup(
        support_dir="support", cache_dir=str(cache), config_file=str(config)
    )
    comtradetools.init("TESTKEY")
    return comtradetools
