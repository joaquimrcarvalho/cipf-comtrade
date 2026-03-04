# Bulk Data Hybrid Implementation Plan

## Overview

This document outlines the plan to modify `comtradetools.py` to use a hybrid data retrieval approach:
- **Historical data (2003-2023)**: Loaded from downloaded bulk CSV files
- **Recent data (2024+)**: Fetched via UN Comtrade API calls

## Motivation

The current implementation relies entirely on API calls, which:
- Are slow due to rate limiting (1 call per 7-20 seconds)
- Can fail due to network issues
- Consume API quota
- Take significant time for historical data spanning 20+ years

Bulk data downloads provide:
- ~100x faster loading for historical data
- No rate limiting issues
- No API quota consumption
- Better reliability

## Architecture

### Core Concept

Create a **transparent hybrid data source** where consumer functions (`getFinalData`, `get_trade_flows`) receive combined data without knowing the source.

```
┌─────────────────┐
│  getFinalData() │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌──────────┐
│ Bulk    │ │ API      │
│ Loader  │ │ Caller   │
│ (pre-   │ │ (2024+)  │
│ 2024)   │ │          │
└────┬────┘ └────┬─────┘
     │           │
     └─────┬─────┘
           │
           ▼
    ┌──────────────┐
    │ Data Merger  │
    │ (concat DF)  │
    └──────────────┘
```

## Components

### 1. New Configuration Constants

Add to `comtradetools.py` (around line 45-62):

```python
# Bulk data configuration
BULK_DATA_DIR = "bulk_data"
BULK_CUTOFF_YEAR = 2024  # Years >= this use API, < this use bulk

# Ensure bulk data directory exists
Path(BULK_DATA_DIR).mkdir(parents=True, exist_ok=True)
```

### 2. New Functions to Add

#### `download_bulk_data(reporter, partner, flow, year)`

Downloads pre-filtered bulk CSV from UN Comtrade bulk download portal.

**Parameters:**
- `reporter` (str): Reporter country M49 code
- `partner` (str): Partner country M49 code
- `flow` (str): Trade flow ('M' for imports, 'X' for exports)
- `year` (int): Year to download

**Returns:** Path to downloaded file or None if failed

**Storage structure:**
```
bulk_data/
├── {reporter_code}/
│   ├── {flow}/
│   │   ├── {year}.csv
```

**UN Comtrade Bulk URL format:**
```
https://comtrade.un.org/api/get/bulk/C/{year}/{reporter_code}?flow={flow}&ps={partner_code}
```

#### `load_bulk_data(reporter, partner, flow, years)`

Loads CSV files from disk for specified years and filters them.

**Parameters:**
- `reporter` (str): Reporter country code
- `partner` (str): Partner country code(s), comma-separated
- `flow` (str): Flow code ('M', 'X', or 'M,X')
- `years` (str): Comma-separated years or year ranges

**Returns:** DataFrame with same structure as API data

**Key operations:**
1. Parse year ranges
2. Load CSV files from `bulk_data/{reporter}/{flow}/{year}.csv`
3. Filter for relevant partners
4. Map column names to API format
5. Return concatenated DataFrame

#### `split_period_by_source(period, cutoff_year)`

Splits period string into bulk vs API ranges.

**Parameters:**
- `period` (str): Period string like "2003,2004,...,2025"
- `cutoff_year` (int): Year threshold (default: BULK_CUTOFF_YEAR)

**Returns:** Tuple `(bulk_periods, api_periods)`

**Example:**
```python
split_period_by_source("2022,2023,2024,2025", 2024)
# Returns: ("2022,2023", "2024,2025")
```

#### `normalize_bulk_columns(df)`

Maps bulk CSV column names to API column names.

**Column mapping:**

| Bulk CSV Column | API Column | Description |
|-----------------|------------|-------------|
| `Year` | `refYear` | Reference year |
| `Reporter` | `reporterDesc` | Reporter country name |
| `Reporter Code` | `reporterCode` | Reporter M49 code |
| `Partner` | `partnerDesc` | Partner country name |
| `Partner Code` | `partnerCode` | Partner M49 code |
| `Trade Flow` | `flowDesc` | Import/Export description |
| `Trade Flow Code` | `flowCode` | 'M' or 'X' |
| `Commodity Code` | `cmdCode` | HS code |
| `Commodity` | `cmdDesc` | HS description |
| `Trade Value (US$)` | `primaryValue` | Trade value in USD |
| `Netweight (kg)` | `netWgt` | Net weight |
| `Quantity` | `qty` | Quantity |
| `Quantity Unit` | `qtyUnitAbbr` | Unit abbreviation |

### 3. Modified Functions

#### `getFinalData()` - Core Changes

Current logic:
```python
def getFinalData(*p, **kwp):
    # ... setup ...
    for subperiod in subperiods:
        # Always call API
        temp = comtradeapicall_getFinalData(*p, **kwp)
        dfs.append(temp)
    return pd.concat(dfs)
```

New hybrid logic:
```python
def getFinalData(*p, **kwp):
    # ... setup ...
    period = kwp.get("period")

    # Split periods by source
    bulk_periods, api_periods = split_period_by_source(period, BULK_CUTOFF_YEAR)

    dfs = []

    # Get historical data from bulk files
    if bulk_periods:
        bulk_df = load_bulk_data(
            reporter=kwp.get("reporterCode"),
            partner=kwp.get("partnerCode"),
            flow=kwp.get("flowCode"),
            years=bulk_periods
        )
        if bulk_df is not None and not bulk_df.empty:
            dfs.append(bulk_df)

    # Get recent data via API
    if api_periods:
        kwp["period"] = api_periods
        api_df = call_api_with_retry(*p, **kwp)  # existing logic
        if api_df is not None and not api_df.empty:
            dfs.append(api_df)

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()
```

#### `init()` - Add bulk data initialization

Add optional bulk data download during initialization:
```python
def init(api_key=None, code_book_url=None, force_init=False,
         download_bulk=False, bulk_years=None):
    # ... existing init logic ...

    if download_bulk and bulk_years:
        download_bulk_data_for_range(bulk_years)
```

### 4. Helper Functions

#### `download_bulk_data_for_range(years, reporters, partners, flows)`

Batch downloads bulk data for specified parameters.

**Default for China-PLP analysis:**
```python
DEFAULT_REPORTERS = ['156', '344', '446', '158']  # China, HK, Macau, Taiwan
DEFAULT_PARTNERS = ['24', '76', '132', '226', '624', '508', '620', '678', '626']  # PLP countries
DEFAULT_FLOWS = ['M', 'X']
```

#### `verify_bulk_data_integrity()`

Checks that bulk data files are complete and valid.

## Data Storage

### Directory Structure

```
bulk_data/
├── README.md                    # Documentation for bulk data
├── manifest.json                # Tracks downloaded files, dates, checksums
├── 156/                         # China
│   ├── M/                       # Imports
│   │   ├── 2003.csv
│   │   ├── 2004.csv
│   │   └── ...
│   └── X/                       # Exports
│       ├── 2003.csv
│       └── ...
├── 344/                         # Hong Kong
│   ├── M/
│   └── X/
├── 446/                         # Macau
│   ├── M/
│   └── X/
└── 158/                         # Taiwan
    ├── M/
    └── X/
```

### Manifest File Format

```json
{
  "version": "1.0",
  "last_updated": "2026-03-04T10:00:00",
  "files": [
    {
      "path": "156/M/2003.csv",
      "reporter": "156",
      "flow": "M",
      "year": 2003,
      "download_date": "2026-03-04",
      "checksum": "sha256:abc123...",
      "record_count": 45000,
      "file_size_bytes": 2500000
    }
  ]
}
```

## Implementation Phases

### Phase 1: Core Infrastructure
- [ ] Add bulk data configuration constants
- [ ] Create `download_bulk_data()` function
- [ ] Create `normalize_bulk_columns()` function
- [ ] Add bulk data directory to `.gitignore`

### Phase 2: Data Loading
- [ ] Create `load_bulk_data()` function
- [ ] Create `split_period_by_source()` function
- [ ] Create `verify_bulk_data_integrity()` function

### Phase 3: Integration
- [ ] Modify `getFinalData()` to use hybrid approach
- [ ] Add bulk data parameters to `init()`
- [ ] Ensure cache compatibility with bulk data

### Phase 4: CLI & Management
- [ ] Add bulk data download management functions
- [ ] Create helper to pre-download China-PLP data
- [ ] Add progress reporting for downloads

### Phase 5: Testing & Documentation
- [ ] Test with existing notebooks
- [ ] Verify data consistency between bulk and API
- [ ] Update documentation

## Usage Examples

### Pre-download bulk data

```python
import comtradetools as ct

# Initialize with bulk data download
ct.init()

# Download all China-PLP historical data
ct.download_bulk_data_for_range(
    years=range(2003, 2024),
    reporters=[ct.m49_china, ct.m49_hong_kong, ct.m49_macau, ct.m49_taiwan],
    partners=ct.m49_plp_list.split(','),
    flows=['M', 'X']
)
```

### Transparent usage in notebooks

```python
import comtradetools as ct

ct.init()

# This will automatically use bulk data for 2003-2023
# and API for 2024-2025
df = ct.getFinalData(
    ct.get_api_key(),
    typeCode="C",
    freqCode="A",
    reporterCode=ct.m49_china,
    partnerCode=ct.m49_plp_list,
    flowCode="M,X",
    period="2003,2004,...,2025",  # Mixed years
    cmdCode="TOTAL"
)
```

### Force API-only mode

```python
# Bypass bulk data and use API only
df = ct.getFinalData(
    ct.get_api_key(),
    period="2003,2004,2005",
    use_bulk=False  # New parameter
)
```

## Benefits

1. **Speed**: Bulk data loads ~100x faster than API calls
2. **Reliability**: No rate limiting or network failures for historical data
3. **Cost**: Zero API calls for historical data
4. **Transparency**: Existing notebooks work unchanged
5. **Offline capability**: Once downloaded, historical data is available offline

## Trade-offs

1. **Storage**: ~50-100MB per year of bulk data (~1-2GB for 2003-2023)
2. **Initial setup**: One-time download of historical data
3. **Maintenance**: Annual bulk data downloads for new historical years
4. **Data freshness**: Bulk data is typically 6-12 months behind API

## Compatibility Considerations

- **Cache system**: Bulk data should work with existing pickle cache
- **Column names**: Ensure all API columns are present in normalized bulk data
- **Data types**: Match data types between bulk and API sources
- **Missing values**: Handle cases where bulk data may have gaps

## Notes for Implementation

1. **UN Comtrade bulk API** requires different authentication than the main API
2. **Bulk files** are typically generated monthly and may lag behind real-time API
3. **Partner filtering**: Some bulk downloads include all partners; filtering happens in `load_bulk_data()`
4. **File compression**: Consider using parquet format instead of CSV for better performance
5. **Incremental updates**: Check manifest before re-downloading existing files
