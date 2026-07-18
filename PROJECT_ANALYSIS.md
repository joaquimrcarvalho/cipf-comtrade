# Project Analysis: cipf-comtrade

## Overview

This is a **Python data analysis project** for accessing and analyzing **UN Comtrade**
(United Nations international trade statistics database) data, specifically focused on
**trade relations between China and Portuguese-speaking countries (PLPs)** and the role
of Macau as a trade platform.

## Project Structure

| Component | Description |
|-----------|-------------|
| **Main Module** | `comtradetools.py` (~1,930 lines) — core utilities for UN Comtrade API access |
| **Notebooks** | 10 Jupyter notebooks for setup and trade analyses |
| **Support** | Reference data, codebooks, HS codes, country codes |
| **Cache** | ~2,476 cached API responses (pickle files, gitignored) |
| **Reports** | ~470 generated reports (375 Excel, 92 PNG) |
| **Docs** | `docs/comtradetools.md` (module manual), `docs/BULK_DATA_IMPLEMENTATION_PLAN.md` |

## Key Features

### 1. API Integration
- Wraps the `comtradeapicall` official package via a single entry point, `getFinalData()`
- Rate limiting (1 call / 20 seconds, bound at import time)
- Automatic pickle caching (90-day validity, `CACHE_VALID_DAYS = 90`)
- Handles API pagination (max 12 periods per request, transparent splitting)
- Forces `partner2Code=0` by default to avoid double counting (see manual §5.1)

### 2. Analysis Capabilities
- Import/export totals between countries, with mirror (partner-reported) values
- Top commodities analysis (HS nomenclature, up to 6-digit)
- Top trading partners ranking
- Trade balance and trade volume calculations
- Product/partner dependency analysis (`total_rank_perc`)

### 3. Portuguese-Speaking Countries Focus
- Angola, Brazil, Cabo Verde, Guinea-Bissau, Equatorial Guinea
- Mozambique, Portugal, São Tomé and Príncipe, Timor-Leste
- Plus: China, Hong Kong, Macau, Taiwan analyses

## Available Notebooks

| Notebook | Purpose |
|----------|---------|
| `0-comtrade-setup-first.ipynb` | First-time setup: API key configuration |
| `cn_plp_import_export.ipynb` | China ↔ PLPs trade flows (+ Forum Macau–comparable Excel tables) |
| `hk_plp_import_export.ipynb` | Hong Kong ↔ PLPs trade |
| `mo_plp_import_export.ipynb` | Macau ↔ PLPs trade |
| `tw_plp_import_export.ipynb` | Taiwan ↔ PLPs trade |
| `cn_plp_commodities.ipynb` | Top commodities analysis |
| `cn_plp_partner2.ipynb` | Partner2 (second partner) analysis — standalone, does not use comtradetools |
| `country_trade_profile.ipynb` | Country trade profiles (products, partners, dependency) |
| `comtrade-api.ipynb` | API exploration sandbox |
| `isaggregate_bug.ipynb` | Reproduction of the HS aggregate double-counting issue |

Most notebooks have companion `*_README.md`/`.pdf` documentation (Portuguese; some English).

## Tech Stack

- **Python 3.10** (`.python-version`: 3.10.9; virtualenv in `venv/`)
- **pandas** — data manipulation
- **matplotlib** — visualization
- **openpyxl/xlsxwriter** — Excel export
- **comtradeapicall** — official UN Comtrade API client
- **ratelimit** — API rate limiting
- **Jupyter + ipywidgets + itables** — interactive analysis

## Dependencies

See `requirements.txt`:

```
pandas, matplotlib, requests, openpyxl, xlsxwriter, tabulate,
ipywidgets, jinja2, ratelimit, comtradeapicall, itables
```

## Configuration

Requires a **UN Comtrade API key** (stored in `config.ini`, gitignored; template in
`config.ini.sample`). Without it the preview endpoint limits results to 500 rows per
request, which can silently produce wrong aggregates.

### Getting an API Key

1. Register at https://comtradedeveloper.un.org/
2. Go to _Products_
3. Select "Premium Individual APIs"
4. Subscribe to "comtrade - v1"
5. Wait for email with API key
6. Run notebook `0-comtrade-setup-first.ipynb` and add the key to `config.ini`

## Main Functions in comtradetools.py

Full reference: **[docs/comtradetools.md](docs/comtradetools.md)**.

| Function | Status | Description |
|----------|--------|-------------|
| `setup()` / `init()` / `get_api_key()` | current | Configure module, load reference codebooks |
| `getFinalData()` | current | Main API wrapper: caching, rate limiting, period splitting |
| `get_trade_flows()` | current | Import/export totals with mirror values |
| `total_rank_perc()`, `subtotal()`, `rank()` | current | DataFrame subtotal/rank/percentage helpers |
| `make_format()` | current | pandas number-format dict builder |
| `excel_col_autowidth()`, `excel_format_currency()`, `excel_format_percent()` | current | Excel formatting |
| `checkAggregateValues()` | current | Flag HS parent (aggregate) codes |
| `encode_country()` / `decode_country()` | current | M49 code ↔ name mapping |
| `year_range()`, `split_period()`, `get_year_intervals()` | current | Period string helpers |
| `get_trade_flows_old()` | DEPRECATED | superseded by `get_trade_flows()` |
| `top_commodities()`, `top_partners()` | DEPRECATED | use `getFinalData()` + pandas ranking |
| `get_data()` | DEPRECATED | raw REST caller predating `comtradeapicall` |

## Directory Structure

```
cipf-comtrade/
├── comtradetools.py          # Main module (manual: docs/comtradetools.md)
├── config.ini                # API configuration (gitignored)
├── config.ini.sample         # Template for config.ini
├── requirements.txt          # Dependencies
├── README.md                 # Documentation (Portuguese)
├── AGENTS.md                 # Agent-oriented project guide
├── *.ipynb                   # Analysis notebooks (10)
├── *_README.md/pdf           # Notebook documentation
├── support/                  # Reference data & codebooks
├── cache/                    # Cached API responses (gitignored, ~2,476 pickles)
├── reports/                  # Generated reports (~470 files)
├── downloads/                # Downloaded files
├── docs/                     # Module manual & design notes
└── web/                      # Web assets (cn_plp_import_export)
```

## Author

**Joaquim Carvalho**, Polytechnic University of Macau

Repository: https://github.com/joaquimrcarvalho/cipf-comtrade.git
