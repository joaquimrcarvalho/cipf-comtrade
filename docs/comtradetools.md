# comtradetools.py — Source Documentation & Manual

Complete reference for the `comtradetools` module (~1,930 lines), the core utility layer
of this project. All notebooks import it; all UN Comtrade API access flows through it.

For orientation and project-wide conventions see `AGENTS.md`; for a project inventory see
`PROJECT_ANALYSIS.md`.

---

## 1. Architecture

```
notebooks
   │
   ├─ setup() / init()                one-time configuration & reference-data loading
   │
   ├─ get_trade_flows()               high-level analysis (import/export totals + mirror data)
   │
   └─ getFinalData()                  general-purpose API wrapper
          │  • splits periods into chunks (≤12 per API call)
          │  • per-chunk pickle cache in cache/ (md5 of parameters)
          │  • forces partner2Code=0 to avoid double counting
          │  • retries on failure / empty results
          ▼
     comtradeapicall_getFinalData()   rate-limited inner wrapper (1 call / 20 s)
          ▼
     comtradeapicall.getFinalData()   official UN Comtrade package
          ▼
     https://comtradeapi.un.org/data/v1/get/   (or /public/v1/preview/ without a key)
```

Design traits to be aware of before editing:

- **Module-level global state.** Configuration (`APIKEY`) and every reference table
  (`COUNTRY_CODES`, `HS_CODES`, …) are module globals populated by `init()`. Notebooks
  depend on this pattern — do not refactor into classes.
- **Two API layers coexist.** The modern path wraps the official `comtradeapicall` package
  (`getFinalData`). The older path (`get_data`) builds raw REST URLs by hand and is
  deprecated, as are `top_commodities`, `top_partners`, `get_trade_flows_old`.
- **Caching is transparent and aggressive.** Identical calls are served from `cache/`
  for 90 days without touching the network. Keep this in mind when testing.

---

## 2. Quick start

Minimal notebook preamble (pattern used across all notebooks):

```python
import comtradetools

comtradetools.setup()                 # create support/, cache/, config.ini if missing
APIKEY = comtradetools.get_api_key()  # read key from config.ini
comtradetools.init(APIKEY)            # load reference tables into module globals

# general query — China's imports (M) from all PLPs, 2020–2022, HS 2-digit
df = comtradetools.getFinalData(
    typeCode="C", freqCode="A", clCode="HS",
    reporterCode=comtradetools.m49_china,          # 156
    partnerCode=comtradetools.m49_plp_list,        # "24,76,132,624,226,508,620,678,626"
    period=comtradetools.year_range(2020, 2022),   # "2020,2021,2022"
    flowCode="M", cmdCode="AG2",
    motCode=0, customsCode="C00",
)

# high-level: import/export totals with mirror (partner-reported) values
tb = comtradetools.get_trade_flows(
    countryOfInterest=comtradetools.m49_china,
    period=comtradetools.year_range(2014, 2023),
    partners=comtradetools.m49_plp_list,
)
```

Running `python comtradetools.py` directly executes the `__main__` block: it creates
`support/`, `reports/`, a stub `config.ini`, then runs `init(APIKEY, force_init=True)`,
which downloads/refreshes all reference tables.

---

## 3. Configuration

### `config.ini`

```ini
[comtrade]
key = YOUR_UN_COMTRADE_API_KEY
```

- Gitignored — never commit. Template: `config.ini.sample`.
- Without a key the module falls back to the public **preview endpoint**, capped at
  **500 rows per request** — this can silently produce wrong aggregates. The literal
  placeholder value `APIKEYHERE` is treated the same as "no key" (`get_url()`).

### Module constants

| Constant | Value | Meaning |
|---|---|---|
| `BASE_URL_PREVIEW` | `https://comtradeapi.un.org/public/v1/preview/` | unauthenticated endpoint |
| `BASE_URL_API` | `https://comtradeapi.un.org/data/v1/get/` | authenticated endpoint |
| `CALLS_PER_PERIOD` | `1` | rate-limit: calls allowed per period |
| `PERIOD_SECONDS` | `20` | rate-limit: period length (seconds) |
| `MAX_RETRIES` | `5` | retries for failed/empty API calls |
| `MAX_SLEEP` | `6` | base backoff between retries (s); actual sleep = `MAX_SLEEP * (RETRY+1)` |
| `CACHE_VALID_DAYS` | `90` | max age of cache entries |
| `SUPPORT_DIR` / `CACHE_DIR` | `support` / `cache` | reference data / pickle cache dirs |
| `CONFIG_FILE` | `config.ini` | config file path |
| `PERC_CMD_IN_PARTNER` | `"perc_cmd_for_partner"` | column label: share of a commodity in a partner's trade |
| `PERC_PARTNER_IN_CMD` | `"perc_partner_for_cmd"` | column label: share of a partner in a commodity's trade |

### PLP country codes (UN M49)

`m49_angola=24`, `m49_brazil=76`, `m49_cabo_verde=132`, `m49_guine_bissau=624`,
`m49_guine_equatorial=226`, `m49_mozambique=508`, `m49_portugal=620`,
`m49_stome_principe=678`, `m49_timor=626`; plus `m49_china=156`, `m49_hong_kong=344`,
`m49_macau=446`.

Aggregates: `m49_plp` (list of ints), `m49_plp_list` (comma-joined string, ready for API
parameters), and after `init()`: `PLP_CODES`, `PLP_CODES_REVERSE`, `PLP_TUPLES`,
`PLP_TUPLES_REVERSE`.

### Reference-data globals (populated by `init()`)

| Global | Source | Content |
|---|---|---|
| `COUNTRY_CODES` | `support/partner.csv` + `reporter.csv` | M49 code → country name (all partners & reporters) |
| `COUNTRY_CODES_REVERSE` | derived | name → M49 code |
| `HS_CODES` | `support/harmonized-system.csv` | HS code → description (all levels) |
| `HS_CODES_L2` | derived | HS 2-digit codes → description |
| `FLOWS_CODES` / `FLOWS_CODES_CAT` | `support/REF FLOWS.csv` | flow code → description / category (M, X variants) |
| `CUSTOMS_CODE` | `support/REF CUSTOMS.csv` | customs procedure code → description |
| `MOS_CODES` | `support/REF  MOS.csv` | mode-of-supply code → description (note: **two spaces** in filename) |
| `MOT_CODES` | `support/REF MOT.csv` | mode-of-transport code → description |
| `QTY_CODES` / `QTY_CODES_DESC` | `support/REF QTY.csv` | quantity unit → abbreviation / full description |
| `COLS_DESC` | `support/COMTRADE+ COMPLETE.csv` | API column → description |
| `DATA_ITEM_DF` | `support/dataitem.csv` | `comtradeapicall.getReference("dataitem")` |
| `APIKEY` | `init()` arg | module-wide API key |
| `INIT_DONE` | — | guard against repeated `init()` (use `force_init=True` to override) |

---

## 4. Function reference

### 4.1 Setup & initialization

#### `setup(support_dir="support", cache_dir="cache", config_file="config.ini")`
Creates the support and cache directories and a stub config file if missing (logs a
warning to add the API key). Updates the `SUPPORT_DIR` / `CACHE_DIR` / `CONFIG_FILE`
globals. Call first in every notebook.

#### `get_api_key() -> str`
Reads `key` from `[comtrade]` in `CONFIG_FILE`. Raises if the file/section is missing.

#### `init(api_key=None, code_book_url=None, force_init=False)`
One-time initialization; a no-op if `INIT_DONE` unless `force_init=True`.

Steps: downloads the codebook (`support/codebook.xlsx`) if missing and exports each
worksheet to `support/<sheet>.csv`; downloads the UNCTAD country-groups CSV; loads every
reference table listed in §3 into globals (fetching `partner`, `reporter`, `dataitem`
references via `comtradeapicall.getReference` when the CSV is absent); loads HS codes;
builds the PLP dicts; **calls `clean_cache()`**, deleting cache entries older than 90 days.

Note on fresh clones: the gitignored `support/REF *.csv` and `COMTRADE+ COMPLETE.csv`
files are **regenerated locally** from worksheets of the committed `support/codebook.xlsx`
— the sheet names match the filenames exactly, including the double-space `REF  MOS`.
Only `Dim_Countries_Hierarchy_UnctadStat_All_Flat.csv` (UNCTAD download) requires network
on first `init()`; `partner.csv`, `reporter.csv`, `dataitem.csv` are committed and only
re-fetched via `comtradeapicall.getReference` if deleted.

#### `clean_cache()`
Deletes every file in `CACHE_DIR` older than `CACHE_VALID_DAYS` (90 days), by file mtime.
Called automatically by `init()`. There is no per-key invalidation — to force a fresh
API response, either delete the specific pickle, pass `cache=False` to `getFinalData`,
or wait out the 90 days.

#### `get_url(api_key=None)`
Returns the authenticated base URL when a real key is given, the preview URL when the
key is `None` or the literal `"APIKEYHERE"`. Used by the deprecated `get_data` only.

### 4.2 Code & period helpers

#### `encode_country(country) `
Country name → M49 code via `COUNTRY_CODES_REVERSE`. Returns the input unchanged if the
name is unknown (a silent pass-through — check outputs rather than assuming failure).

#### `decode_country(country_code)`
M49 code → country name via `COUNTRY_CODES`. Same pass-through behavior. The dict is
keyed by **integer** codes — the signature accepts `Union[str, int]`, but pass ints.

#### `year_range(year_start=1984, year_end=2030) -> str`
Returns `"1984,1985,…,2030"` — the comma-separated period format the API expects.

#### `split_period(period, max_periods=12) -> list[str]`
Splits a comma-separated period string into chunks of at most `max_periods`. Used by
`getFinalData` to respect the API's 12-periods-per-call limit.

#### `get_year_intervals(years) -> list[str]`
Collapses a sorted list of years into interval strings:
`[2018,2019,2021] → ["2018-2019", "2021-2021"]`. Used for report titles/labels, not API
calls.

### 4.3 Core data access: `getFinalData`

#### `getFinalData(*p, **kwp) -> pd.DataFrame`

The single entry point for all modern API queries. Signature is intentionally generic:
one optional positional argument (the API key — defaults to `get_api_key()` from
`config.ini` when omitted; **not** the `APIKEY` global) plus keyword arguments forwarded
to `comtradeapicall.getFinalData` (`typeCode`, `freqCode`, `clCode`, `reporterCode`,
`partnerCode`, `partner2Code`, `period`, `cmdCode`, `flowCode`, `motCode`,
`customsCode`, `includeDesc`, … — see the
[comtradeapicall docs](https://github.com/uncomtrade/comtradeapicall)).

Wrapper-specific keyword arguments (consumed by the wrapper, not forwarded):

| Arg | Default | Effect |
|---|---|---|
| `cache` | `True` | cache each period-chunk result as a pickle in `cache/` |
| `retry_if_empty` | `True` | discard cached empty results and re-fetch |
| `remove_world` | `False` | drop `partnerCode == 0` rows from the final result (relevant when `partnerCode=None`) |
| `period_size` | `12` | chunk size for period splitting |
| `use_alternative` | `False` | use `comtradeapicall._getFinalData` (private, "optimized" variant — untested) |

Behavior, in order:

1. Defaults `partner2Code` to `0` if not given — **this is load-bearing**, see §5.1.
2. Requires `period`; raises `ValueError` otherwise.
3. Splits oversized comma-separated `cmdCode`/`reporterCode`/`partnerCode` lists
   (more than `CSV_BATCH_MAX_ITEMS` = 100 items) into batches — the API rejects
   request URLs over ~2000 characters, and ~190 HS6 codes with a typical
   reporter list already cross that (see §5.6). Each batch is a recursive call
   with the same wrapper arguments and its own cache entries; batch results are
   concatenated before returning.
4. Splits `period` via `split_period(period, period_size)` and processes each chunk:
   - Computes an `md5` of the sorted parameter items (+ `use_alternative`) →
     `cache/<hash>.pickle` (order-independent since 2026-07-21; older pickles
     are unreachable).
   - Fresh-enough cache hit (≤ 90 days) → load; empty cached frame → re-fetch unless
     `retry_if_empty=False`; stale → delete and re-fetch.
   - Miss → call the rate-limited inner wrapper. On exception: one immediate retry.
     On `None` result: up to `MAX_RETRIES` (5) attempts with linear backoff
     (`MAX_SLEEP * (RETRY+1)` seconds), then raises `IOError`.
   - Successful non-empty chunks are written to cache; all-NA frames are dropped with a warning.
5. Concatenates chunks; applies `remove_world` if requested.

Returns an **empty DataFrame** (not `None`) when every chunk came back empty.
Cached results are returned instantly — the rate limiter only guards live calls.

#### `comtradeapicall_getFinalData(*p, **kwp)`
Thin inner wrapper decorated with `@sleep_and_retry` + `@limits(calls=1, period=20)`.
Not meant to be called directly. Note: the decorator arguments are evaluated **at import
time** — assigning to `comtradetools.PERIOD_SECONDS` or `CALLS_PER_PERIOD` afterwards
(as some notebooks and the `__main__` block do) has **no effect** on the actual rate limit.

### 4.4 High-level analysis

#### `get_trade_flows(countryOfInterest=None, period=None, typeCode="C", freqCode="A", partners=0, period_size=1, retry_if_empty=True, symmetric_values=True)`

Import/export totals for one country against the world or a set of partners — the current,
supported version (supersedes `get_trade_flows_old`).

Makes up to four `getFinalData` calls, all with `cmdCode="TOTAL"`, `motCode=0`,
`customsCode="C00"`, `partner2Code=0`, `includeDesc=True`:

| Result | reporterCode | partnerCode | flowCode |
|---|---|---|---|
| reported imports | country of interest | partners | M |
| reported exports | country of interest | partners | X |
| mirror exports `X<M` | partners (None if world) | country of interest | M |
| mirror imports `M<X` | partners (None if world) | country of interest | X |

The mirror calls (`symmetric_values=True`, the default) recover the country's exports as
**reported by its partners' imports** (`X<M`) and vice versa (`M<X`) — essential when the
country of interest reports poorly (e.g. some PLPs in some years).

Returns a pivot DataFrame indexed by `period` with one column per flow present plus
derived columns (each added only when its inputs exist):

- `trade_balance (X-M)`, `trade_balance (X<M-M)`, `trade_balance (X<M-M<X)`
- `trade_volume (X+M)`, `trade_volume (X<M+M)`, `trade_volume (X<M+M<X)`

Mirror values normally differ from directly reported ones (CIF vs FOB valuation, partner
attribution, reporting gaps) — surface both, never "reconcile" them.

### 4.5 Deprecated functions (kept for backward compatibility)

| Function | Status | Replacement |
|---|---|---|
| `get_trade_flows_old(...)` | DEPRECATED | `get_trade_flows()` (adds `period_size`, `retry_if_empty`, more balance columns) |
| `top_commodities(reporterCode, partnerCode=0, years=None, flowCode="M,X", partner2Code=0, cmdCode="AG2", motCode=None, rank_filter=5, return_data=False, timeout=120, echo_url=False)` | DEPRECATED | `getFinalData` + pandas ranking (see `cn_plp_commodities.ipynb`) |
| `top_partners(reporterCode=0, years=None, cmdCode="TOTAL", flowCode="M,X", partnerCode=None, partner2Code=0, motCode=0, customsCode="C00", rank_*_filter=None, return_data=False, ...)` | DEPRECATED | `getFinalData` + pandas ranking (see `country_trade_profile.ipynb`) |
| `get_data(typeCode, freqCode, reporterCode="156", partnerCode=<PLPs>, partner2Code=0, period=None, clCode="HS", cmdCode="TOTAL", flowCode="M,X", customsCode="C00", more_pars=None, qtyUnitCodeFilter=None, motCode=None, apiKey=None, cache=True, timeout=10, echo_url=False)` | DEPRECATED | `getFinalData()` — `get_data` hand-builds REST URLs and predates the official package |

The deprecated `top_*` functions still work and document the project's standard
enrichment columns (`sum_*`, `perc_*`, `rank_*`, `perc_cmd_for_partner`,
`perc_partner_for_cmd`) — useful reading even if you don't call them.

### 4.6 DataFrame utilities

#### `subtotal(df, groupby, col)`
`df.groupby(groupby)[col].transform("sum")` — per-group sum aligned to the original rows.

#### `rank(df, rankby, col)`
Dense descending rank of `col` within each `rankby` group, as `int`.

#### `total_rank_perc(df, groupby, col, prefix, rankby=None, percby=None, drop_duplicates=True)`
Adds five columns summarizing `col` over `groupby`:

- `{prefix}_sum` — subtotal per full group
- `{prefix}_rank` — rank of the group subtotal within `rankby` (default `groupby[:-1]`)
- `{prefix}_perc` — row value as share of the parent-group subtotal
- `{prefix}_upper_sum` — parent-group subtotal (`groupby[:-1]`)
- `{prefix}_upper_perc` — group subtotal as share of the parent subtotal

Then drops duplicate rows on `groupby` (disable with `drop_duplicates=False`).
**Mutates the input frame** while computing. Used heavily by `country_trade_profile.ipynb`
(e.g. rank products within year × flow, with the share of each product in the year total).

#### `make_format(cols) -> dict`
Builds a pandas format dict: `{0:.3%}` for columns ending in `perc`, `${0:,.0f}` for
columns ending in `sum` and for `primaryValue`. For `DataFrame.style.format(...)` or
`to_excel` post-processing.

### 4.7 Excel export (xlsxwriter via `pd.ExcelWriter`)

Pattern used in notebooks:

```python
with pd.ExcelWriter("reports/out.xlsx", engine="xlsxwriter") as writer:
    df.to_excel(writer, sheet_name="data")
    comtradetools.excel_col_autowidth(df, writer, sheet="data")
    comtradetools.excel_format_currency(df, writer, sheet="data", columns=["primaryValue"])
    comtradetools.excel_format_percent(df, writer, sheet="data", columns=["perc_x"])
```

- `excel_col_autowidth(data_frame, excel_file, sheet=None, consider_headers=True)` —
  sets each column's width to the longest content (headers included, capped at 100);
  handles multi-level indices. Column offset accounting depends on the number of index
  levels — call it on the same frame you wrote.
- `excel_format_currency(..., columns=None, format_currency="$#,##0", width=None)` —
  defaults to all numeric columns.
- `excel_format_percent(..., columns=None, format_perc="0.00%", width=None)` —
  same defaults.

### 4.8 Validation

#### `checkAggregateValues(df, hcode_column, aggregate_column="isCmdAggregate")`
Flags rows whose hierarchical code is a **parent** of the next row's code (e.g. `"01"`
followed by `"0101"` → `"01"` is an aggregate). Requires the frame to be **sorted
ascending by `hcode_column`** (a TODO in the source notes the function could sort itself).
Warns on duplicated codes. Used to avoid double counting when mixing HS levels —
see `isaggregate_bug.ipynb` for the motivating bug.

---

## 5. Data semantics & pitfalls

### 5.1 The `partner2Code` double-counting trap

When an API call omits `partner2Code`, UN Comtrade may return, for the same
reporter/partner/year, one row per second partner **plus** an extra row with
`partner2Code = 0` containing their aggregate — i.e. the total appears twice if you sum
naively. `getFinalData` therefore **forces `partner2Code=0`** unless you explicitly pass
another value. Pass `partner2Code=None` only if you genuinely want the breakdown (and
then deduplicate yourself). The docstring of `getFinalData` carries a worked example
(China → Equatorial Guinea, 2015).

### 5.2 `partnerCode=None` includes the World row

With `partnerCode=None` the API returns both the world (`partnerCode=0`) and every
individual partner. Use `remove_world=True` (or filter `df.partnerCode != 0`) before
aggregating, or totals double.

### 5.3 Aggregate rows and mixed granularity

Queries spanning several HS levels (e.g. `AG2` + specific codes) can return both parents
and children. Watch the `isAggregate` column and use `checkAggregateValues` when in doubt.
The same class of problem exists for `motCode` (0 = all modes) and `customsCode`
(C00 = all procedures): the deprecated `get_data` warns when a result mixes aggregates
with details; `getFinalData` does not — pass explicit `motCode=0, customsCode="C00"`
as the notebooks do.

### 5.4 Empty results

No data for a (country, year, flow) combination is a normal occurrence, not an error:
empty chunks are skipped and the wrapper returns an empty DataFrame. A `None` return from
the underlying package is retried and ultimately raises `IOError` — treat persistent
`IOError` as "API unreachable or query rejected", not "no data".

### 5.5 Cache key sensitivity

The cache hash covers the full forwarded parameter dict (after wrapper-only args are
stripped) **plus the sub-period string**. Parameters are sorted before hashing, so the
key is order-independent (since 2026-07-21; pickles written before that date use the
old order-sensitive key and are unreachable). Consequences:

- One pickle per period chunk — a 30-year query = 3 cache files at `period_size=12`,
  30 files at `period_size=1`. The same logical query with different `period_size`
  populates different cache entries.
- Any parameter value change (including cosmetic ones like `includeDesc`) yields a
  new entry — but parameter *order* no longer matters.
- Cached frames are returned as pickled — column sets reflect the call that created them.

### 5.6 Long CSV code lists hit the API's URL length limit

The UN Comtrade server rejects request URLs longer than ~2000 characters with
"Request URL exceeds maximum allowed length (2000 characters)" (a server-side
message printed by `comtradeapicall`, followed by `getFinalData`'s empty-result
retries). Long comma-separated `cmdCode`/`reporterCode`/`partnerCode` lists are
what blows the budget: commas are URL-encoded as `%2C`, so a single HS6 code
costs ~9 characters, and the `subscription-key` itself travels in the query
string. Example (verified 2026-07-22): 104 HS6 codes + 24 reporters ≈ 1200
chars — accepted; 178 HS6 codes + 23 reporters ≈ 1950+ chars — rejected.

`getFinalData` prevents this by splitting any CSV list longer than
`CSV_BATCH_MAX_ITEMS` (100) into batches (§4.3 step 3). If you ever see the
error anyway, shorten the lists yourself — or split one of the *other*
parameters, since the limit applies to the whole URL.

### 5.7 Rate limiting is import-time bound

`@limits(calls=CALLS_PER_PERIOD, period=PERIOD_SECONDS)` freezes `1 / 20 s` at import.
Reassigning the constants later changes nothing (some notebooks do this — it is a no-op).
To actually change the limit, edit the constants at the top of the file before import.
Note also that premium Comtrade keys allow higher rates — the 20 s default is
conservative; `comtradeapicall`'s own limiter may also apply.

### 5.8 Misc quirks

- `encode_country` / `decode_country` never fail loudly: unknown inputs pass through
  unchanged — check outputs rather than assuming failure.

---

## 6. Where things are used

| Consumer | comtradetools API used |
|---|---|
| `0-comtrade-setup-first.ipynb` | `setup`, `get_api_key`, `init` |
| `cn_plp_import_export.ipynb`, `hk_/mo_/tw_plp_import_export.ipynb` | `getFinalData`, `year_range`, `split_period` |
| `cn_plp_commodities.ipynb` | `getFinalData`, `year_range`, `encode_country`, `excel_col_autowidth`, `excel_format_currency`, M49 constants |
| `country_trade_profile.ipynb` | `get_trade_flows`, `getFinalData`, `total_rank_perc`, `make_format`, `year_range`, `HS_CODES`, `encode_country` |
| `comtrade-api.ipynb` | `getFinalData`, `year_range`, `decode_country` (API exploration/sandbox) |
| `isaggregate_bug.ipynb` | `decode_country` (repro for the aggregate-values issue, §4.8) |
| `cn_plp_partner2.ipynb` | (does not import comtradetools) |
