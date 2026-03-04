# Project Analysis: cipf-comtrade

## Overview

This is a **Python data analysis project** for accessing and analyzing **UN Comtrade** (United Nations international trade statistics database) data, specifically focused on **trade relations between China and Portuguese-speaking countries (PLPs)** and the role of Macau as a trade platform.

## Project Structure

| Component | Description |
|-----------|-------------|
| **Main Module** | `comtradetools.py` (~1,900 lines) - Core utilities for UN Comtrade API access |
| **Notebooks** | 8+ Jupyter notebooks for various trade analyses |
| **Support** | Reference data, codebooks, HS codes, country codes |
| **Cache** | 372 cached API responses (pickle files) |
| **Reports** | 302 generated reports |

## Key Features

### 1. API Integration
- Wraps the `comtradeapicall` official package
- Rate limiting (1 call/20 seconds)
- Automatic caching (60-day validity)
- Handles API pagination (max 12 periods per request)

### 2. Analysis Capabilities
- Import/export totals between countries
- Top commodities analysis (HS nomenclature)
- Top trading partners ranking
- Trade balance calculations
- Symmetric value reporting (reporter vs. partner perspectives)

### 3. Portuguese-Speaking Countries Focus
- Angola, Brazil, Cabo Verde, Guinea-Bissau, Equatorial Guinea
- Mozambique, Portugal, São Tomé and Príncipe, Timor-Leste
- Plus: China, Hong Kong, Macau, Taiwan analyses

## Available Notebooks

| Notebook | Purpose |
|----------|---------|
| `cn_plp_import_export.ipynb` | China ↔ PLPs trade flows |
| `hk_plp_import_export.ipynb` | Hong Kong ↔ PLPs trade |
| `mo_plp_import_export.ipynb` | Macau ↔ PLPs trade |
| `tw_plp_import_export.ipynb` | Taiwan ↔ PLPs trade |
| `cn_plp_commodities.ipynb` | Top commodities analysis |
| `country_trade_profile.ipynb` | Country trade profiles |
| `comtrade-api.ipynb` | API exploration |

## Tech Stack

- **Python 3** (version in `.python-version`)
- **pandas** - Data manipulation
- **matplotlib** - Visualization
- **openpyxl/xlsxwriter** - Excel export
- **comtradeapicall** - Official UN Comtrade API client
- **ratelimit** - API rate limiting
- **Jupyter** - Interactive analysis

## Dependencies

```
pandas
matplotlib
requests
openpyxl
xlsxwriter
tabulate
ipywidgets
jinja2
ratelimit
comtradeapicall
itables
```

## Configuration

Requires a **UN Comtrade API key** (stored in `config.ini`). Without it, results are limited to 500 rows per request.

### Getting an API Key

1. Register at https://comtradedeveloper.un.org/
2. Go to _Products_
3. Select "Premium Individual APIs"
4. Subscribe to "comtrade - v1"
5. Wait for email with API key
6. Add key to `config.ini`

## Main Functions in comtradetools.py

| Function | Description |
|----------|-------------|
| `init()` | Initialize module, load codebooks |
| `getFinalData()` | Main API wrapper with caching and rate limiting |
| `get_trade_flows()` | Get import/export totals for a country |
| `top_commodities()` | Get top traded commodities |
| `top_partners()` | Get top trading partners |
| `year_range()` | Generate year range strings |
| `excel_col_autowidth()` | Excel formatting utilities |

## Directory Structure

```
cipf-comtrade/
├── comtradetools.py          # Main module
├── config.ini                # API configuration
├── requirements.txt          # Dependencies
├── README.md                 # Documentation
├── *.ipynb                   # Analysis notebooks
├── *_README.md/pdf           # Notebook documentation
├── support/                  # Reference data & codebooks
├── cache/                    # Cached API responses
├── reports/                  # Generated reports
├── downloads/                # Downloaded files
└── web/                      # Web assets
```

## Author

**Joaquim Carvalho**, Polytechnic University of Macau

Repository: https://github.com/joaquimrcarvalho/cipf-comtrade.git
