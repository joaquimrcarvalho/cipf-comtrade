# AGENTS.md

## Project overview

Python/Jupyter data-analysis project for **UN Comtrade** trade statistics, focused on trade
between **China and the Portuguese-speaking countries (PLPs)** and Macau's role as a platform.
Author: Joaquim Carvalho, Universidade Politécnica de Macau.

The deliverables are **notebooks** and their generated outputs (Excel tables + PNG charts in
`reports/`). Tests live in `tests/` (pytest, no network — the API layer is mocked); there is
no package build.

## Layout

- `comtradetools.py` — single core module (~1,930 lines). All API access, caching, reference
  data, and Excel helpers live here. Notebooks import it; keep logic here rather than in notebooks.
- `*.ipynb` — 10 analysis notebooks (China/HK/Macau/Taiwan ↔ PLP flows, commodities, country profiles).
- `*_README.md` — per-notebook documentation, mostly in **Portuguese** (project's working
  language; an `_EN` variant exists for some). Match the existing language when editing docs.
- `support/` — reference data: codebook, HS codes, M49 country codes, partner/reporter CSVs.
- `cache/` — pickled API responses (~2,476 files). Gitignored. Do not delete casually.
- `reports/` — generated outputs (`.xlsx`, `.png`). Filenames follow
  `<Country|China>_<section>_<description>_<years>.<ext>` — keep this convention.
- `docs/` — `comtradetools.md` (**full module manual — read it before non-trivial changes
  to `comtradetools.py`**), `BULK_DATA_IMPLEMENTATION_PLAN.md` (planned bulk-download support).
- `config.ini` — API key, **gitignored, never commit or print it**. `config.ini.sample` is the template.

## Environment & setup

- Python **3.10** (`.python-version`), dependencies in `requirements.txt`; virtualenv in `venv/`
  (`source venv/bin/activate`).
- Run tests with `venv/bin/python -m pytest tests/ -q` (31 tests, all offline; `conftest.py`
  at repo root puts the repo on `sys.path` and provides the hermetic `ctt` init fixture).
- A UN Comtrade API key goes in `config.ini` (`[comtrade] key = ...`). Without it the public
  preview endpoint caps results at **500 rows**, which can silently produce **wrong aggregates**.
- First-time setup is done via notebook `0-comtrade-setup-first.ipynb`.

## How the code works (important for edits)

Full function-by-function reference: **`docs/comtradetools.md`**. Essentials:

### Architecture

```
notebooks ──► get_trade_flows() ─┐
                                 ├─► getFinalData() ──► comtradeapicall_getFinalData() ──► UN Comtrade API
notebooks ──► getFinalData() ────┘        (cache + period split)      (rate limit 1/20 s)
```

- **Module-level global state.** `init()` populates globals (`APIKEY`, `COUNTRY_CODES`,
  `HS_CODES`, …) from `support/` reference files (downloading them if missing) and then
  calls `clean_cache()`. Notebooks call `setup()` → `get_api_key()` → `init(APIKEY)` once
  per session; `INIT_DONE` guards re-init unless `force_init=True`.
- **`getFinalData()` is the single API entry point.** It forces `partner2Code=0`
  (prevents double counting — manual §5.1), splits `period` into ≤12-period chunks
  (`split_period()`; one **cache pickle per chunk**), retries failures (`MAX_RETRIES=5`,
  linear backoff, then `IOError`), and caches each chunk for `CACHE_VALID_DAYS = 90`.
  When testing API-facing changes, expect cached results — pass `cache=False` or clear
  the specific pickle to force a live call. Returns an **empty DataFrame**, not `None`,
  when there is no data.
- **Wrapper-only kwargs** consumed by `getFinalData` (not forwarded to the API):
  `cache`, `retry_if_empty`, `remove_world`, `period_size`, `use_alternative`.
- **Rate limit is frozen at import time** by the `@limits(calls=1, period=20)` decorator.
  Reassigning `PERIOD_SECONDS`/`CALLS_PER_PERIOD` after import (some notebooks and the
  `__main__` block do this) has **no effect** — edit the constants in the file instead.
- **Mirror (symmetric) data**: `get_trade_flows()` reports flows `X`, `M` plus `X<M`
  (exports inferred from partners' imports) and `M<X` (imports inferred from partners'
  exports). Values legitimately differ (CIF/FOB, reporting gaps) — surface both.
- Countries are **UN M49 numeric codes**. Use the module constants (`m49_china`,
  `m49_plp_list`, …), never hardcoded numbers (China is `156`).
- Excel output styling goes through `excel_col_autowidth()`, `excel_format_currency()`,
  `excel_format_percent()`. Reuse them for new reports.
- Trade values are in **current US dollars**; percentage columns use the module's
  `PERC_CMD_IN_PARTNER` / `PERC_PARTNER_IN_CMD` labels.

### Deprecated code — do not extend

| Function | Use instead |
|---|---|
| `get_trade_flows_old()` | `get_trade_flows()` |
| `top_commodities()`, `top_partners()` | `getFinalData()` + pandas ranking (see `cn_plp_commodities.ipynb`, `country_trade_profile.ipynb`) |
| `get_data()` | `getFinalData()` |

### Common pitfalls (details in manual §5)

- `partnerCode=None` returns a World row (`partnerCode=0`) alongside partners —
  use `remove_world=True` before aggregating.
- Mixing HS levels or `motCode`/`customsCode` aggregates with details double-counts;
  `checkAggregateValues()` flags HS parent codes (see `isaggregate_bug.ipynb`).
- Any parameter change (even `includeDesc`) creates a new cache entry; `clean_cache()`
  runs on every `init()` and deletes entries older than 90 days.
- `encode_country`/`decode_country` pass unknown inputs through unchanged instead of
  failing — check outputs.

## Conventions

- Code, identifiers, and comments in English; user-facing docs/reports largely in Portuguese.
- Style: PEP 8, `max-line-length = 100` (`.flake8`), though `comtradetools.py` disables E501.
  Docstrings use Google style (`Args:` / `Returns:`).
- The module relies on module-level globals for config (`APIKEY`, reference DataFrames);
  preserve this pattern rather than refactoring to classes — notebooks depend on it.
- Notebooks are executed interactively; outputs are committed. Keep notebooks runnable
  top-to-bottom (`jupyter nbconvert --execute` should succeed).

## Gotchas

- `support/` CSVs with spaces in names (`REF  MOS.csv` — note the double space) are referenced
  by exact filename; don't rename. Gitignored `REF *.csv` files regenerate from
  `support/codebook.xlsx` worksheets on `init()` (see manual §4.1).
- `docs/BULK_DATA_IMPLEMENTATION_PLAN.md` describes planned bulk-download support — check it
  before adding new data-access paths.
