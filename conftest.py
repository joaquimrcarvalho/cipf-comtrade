"""Pytest bootstrap: make the repo root importable and provide shared fixtures."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Support files init() needs but that are NOT committed in git:
# - "REF *.csv" and "COMTRADE+ COMPLETE.csv" are regenerated locally by init()
#   from the committed codebook.xlsx worksheets, so they need no check.
# - "Dim_Countries_Hierarchy_UnctadStat_All_Flat.csv" would be downloaded from
#   UNCTAD, but comtradetools never reads it (init() only downloads it), so a
#   placeholder keeps the suite fully offline (created below if missing).
# Only the committed files are hard requirements; without them init() would
# hit the network (comtradeapicall.getReference / HS code download).
REQUIRED_SUPPORT_FILES = [
    "codebook.xlsx",
    "dataitem.csv",
    "partner.csv",
    "reporter.csv",
    "harmonized-system.csv",
]

COUNTRY_GROUPS_FILE = Path("support/Dim_Countries_Hierarchy_UnctadStat_All_Flat.csv")


@pytest.fixture(scope="session")
def ctt(tmp_path_factory):
    """Import and initialize comtradetools the way the notebooks do, but hermetically.

    Uses a throwaway config.ini (dummy key) and a throwaway cache dir so tests
    never touch the real config or the real cache. Skips only if a committed
    support file is absent, because init() would then need network access.
    """
    support = Path("support")
    missing = [f for f in REQUIRED_SUPPORT_FILES if not (support / f).is_file()]
    if missing:
        pytest.skip(f"committed support files missing, init() needs network: {missing}")

    import comtradetools

    tmp = tmp_path_factory.mktemp("ctt")
    config = tmp / "config.ini"
    config.write_text("[comtrade]\nkey = TESTKEY\n")
    cache = tmp / "cache"

    comtradetools.setup(
        support_dir="support", cache_dir=str(cache), config_file=str(config)
    )

    # Placeholder so init() skips the UNCTAD download; the file is never read.
    created_placeholder = False
    if not COUNTRY_GROUPS_FILE.is_file():
        COUNTRY_GROUPS_FILE.write_text("")
        created_placeholder = True

    comtradetools.init("TESTKEY")

    yield comtradetools

    if created_placeholder:
        COUNTRY_GROUPS_FILE.unlink()
