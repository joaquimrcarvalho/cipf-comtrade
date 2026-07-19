# Site Specification — China ↔ PLP Trade Observatory

**Status:** Draft v1.0 (2026-07-19)
**Author:** Joaquim Carvalho (with AI assistance)
**Target platform:** [Observable Framework](https://observablehq.com/framework/what-is-framework) → static build → **GitHub Pages**

---

## 1. Purpose and goals

Publish the results of the `cipf-comtrade` research project as a **public, fast, static
website** with interactive data visualization, replacing the current distribution channel
(Excel files + PNG charts in `reports/`, plus PDF READMEs) with an explorable web experience.

The site's subject: **trade between China and the Portuguese-speaking countries (Países de
Língua Portuguesa — PLPs)** and the role of Macau (RAEM) as a platform, based on UN Comtrade data.

### Goals

1. Make the project's core datasets explorable in the browser (time series, rankings,
   product/partner composition) without requiring Excel or Jupyter.
2. Keep the site's data **reproducible from the existing Python pipeline**
   (`comtradetools.py` + cached UN Comtrade API responses) — no parallel data logic.
3. Fully static hosting on GitHub Pages: no server, no database, no client-side API calls
   to UN Comtrade.
4. Present data with the same rigor as the notebooks: direct vs. mirror (symmetric) values
   surfaced, units explicit, sources cited.

### Non-goals (v1)

- No live querying of the UN Comtrade API from the browser.
- No user accounts, comments, or CMS.
- No full country-profile depth for all 9 PLPs on day one (see phased roadmap, §11).
- No bilingual parity at launch (Portuguese first; English later, §6.4).

---

## 2. Audience and language

| Audience | Need |
|---|---|
| Researchers / students (Forum Macau, CPLP studies, trade economics) | Trustworthy figures, citable tables, methodology notes |
| Policy / institutional readers (Macau SAR, Forum Macau) | Headline charts, trade balance and top partners at a glance |
| General public / press | Clear Portuguese-language narrative around the numbers |

- **Site UI language: Portuguese (European)** — the project's working language
  (labels like *Trocas comerciais, Exportações, Importações, Saldo comercial*).
- **Code, file names, and commit messages in English** (project convention).
- Methodology pages cite UN Comtrade and note the Macau/Forum Macau validation angle.

---

## 3. Source data inventory (what we publish)

All site data derives from the existing pipeline. The notebooks below are the **canonical
definitions** of each dataset; the site must not re-derive numbers differently.

| ID | Dataset | Source notebook | Shape (grain) | Existing output (reference) |
|----|---------|-----------------|---------------|------------------------------|
| D1 | China ↔ PLP flows: year × PLP, with Exportações, Importações, Trocas (volume), Saldo | `cn_plp_import_export.ipynb` | year (2003–latest) × 9 PLPs | `reports/cn_plp_trocas_2003-*.xlsx`, `quadros_forum_*.xlsx`, `cn_plp_{Trocas,Importações,Exportações,Saldo}.png` |
| D2 | Macau (RAEM) ↔ PLP flows | `mo_plp_import_export.ipynb` | year × 9 PLPs, same measures | `reports/mo_plp_*` |
| D3 | Hong Kong (RAEHK) ↔ PLP flows | `hk_plp_import_export.ipynb` | year × 9 PLPs | `reports/hk_plp_*` |
| D4 | Taiwan (Prov. China) ↔ PLP flows | `tw_plp_import_export.ipynb` | year × 9 PLPs; reporter code **490** ("Other Asia, nes" — see [UN Comtrade note](https://uncomtrade.org/docs/taiwan-province-of-china-trade-data/)) | `reports/tw_plp_*` |
| D5 | Country trade profile — trade balance (direct vs. mirror) | `country_trade_profile.ipynb` §1 | year × country: X, M, X<M, M<X, balance | `<C>_1.1_trade_balance_*.xlsx`, `_1.2_*.png` |
| D6 | Profile — top export partners / top import origins | §2.1, §3.1 | year × partner (top-N + %) | `<C>_2.1.x_*`, `<C>_3.1.x_*` |
| D7 | Profile — top exported / imported products (HS-AG6) | §2.2, §3.2 | year × HS6 product (top-N + %) | `<C>_2.2_*`, `<C>_3.2_*` |
| D8 | Profile — product×partner decomposition (who buys the oil; what does China buy) | §2.3, §2.4, §3.3, §3.4 | year × product × partner | `<C>_2.3_*`, `<C>_2.4_*`, … |
| D9 | China ↔ PLP top commodities | `cn_plp_commodities.ipynb` | year × HS chapter/heading × flow | `reports/cn_plp_*commod*` |
| D10 | Reference dimensions | `support/` (REF COUNTRIES, harmonized-system) | country list, HS code→description | `support/*.csv`, `codebook.xlsx` |

**Terminology (must be consistent site-wide):**
- *direct* = values reported by the country under analysis;
- *reverse/mirror* = values inferred from partners' reports (exports inferred from partners'
  imports, `X<M`; imports inferred from partners' exports, `M<X`).
- CIF/FOB and reporting gaps make direct ≠ mirror; **both must be visible or switchable**,
  never silently mixed (see AGENTS.md / `docs/comtradetools.md` §5).

---

## 4. Technical architecture

### 4.1 Repository strategy

The Framework project lives **inside this repository** at `site/` (monorepo). Rationale:

- Data loaders / export scripts can `import comtradetools` and read `cache/` directly.
- One repo = one history for data + presentation; GitHub Actions deploys from the same repo.
- GitHub Pages workflow builds from `site/` and publishes `site/dist` (§8).

```
cipf-comtrade/
├── comtradetools.py          # unchanged — single source of data logic
├── cache/                    # local API cache (gitignored) — input for exports
├── reports/                  # existing Excel/PNG outputs (unchanged)
├── site/                     # ← NEW: Observable Framework project
│   ├── observablehq.config.ts
│   ├── package.json
│   ├── src/
│   │   ├── index.md                # landing page / dashboard
│   │   ├── china-plp.md            # D1 explorer
│   │   ├── macau.md hong-kong.md taiwan.md
│   │   ├── perfis/angola.md …      # country profiles (D5–D8)
│   │   ├── metodologia.md          # methodology & sources
│   │   ├── data/                   # committed data snapshots (§5)
│   │   ├── loaders/                # regeneration entry points (thin .py wrappers)
│   │   └── components/             # shared JS chart components
│   └── scripts/export_site_data.py # master export: comtradetools → site/src/data
└── .github/workflows/deploy.yml
```

Alternative considered and rejected: separate repo for the site (breaks direct access to
`comtradetools` and the cache; forces publishing intermediate data artifacts anyway).

### 4.2 Data flow

```
UN Comtrade API ──► comtradetools.getFinalData() ──► cache/*.pickle
                                                          │
                          site/scripts/export_site_data.py (run locally, uses venv)
                                                          │
                                       site/src/data/*.csv|json  (committed snapshots)
                                                          │
                              Observable Framework build (FileAttachment)
                                                          │
                                            static dist/ ──► GitHub Pages
```

**Key decision — committed snapshots, not CI-time API pulls.**
The UN Comtrade rate limit (1 call / 20 s) and the 500-row preview cap make CI-time
extraction slow and fragile. Therefore:

- v1: `export_site_data.py` runs **locally** (where `cache/` and `config.ini` exist),
  writes tidy CSV/JSON into `site/src/data/`, which are **committed** and referenced by
  pages via `FileAttachment("data/....csv")`. The Framework build needs no API key.
- v2 (optional): scheduled GitHub Action re-runs the export with the API key stored as a
  repo secret, using `actions/cache` for `src/.observablehq/cache` and the loader cache
  pattern from Framework's deploying guide; opens a PR with updated snapshots for review.

### 4.3 Framework mechanics to use

- **Pages**: Markdown with fenced ```js code blocks (Framework's reactive runtime).
- **Data access**: `FileAttachment(...).csv({typed: true})` / `.json()`; all data shipped
  from `_file/` at build, pre-aggregated to the exact grain the charts need.
- **Charts**: Observable Plot first; D3 for custom work; `Inputs` for controls
  (country selector, year range, direct/mirror toggle, flow selector).
- **Tables**: `Inputs.table` for sortable/searchable tabular views (replaces the current
  itables HTML fragment in `web/`, which depends on external CDNs and will be superseded).
- **Config**: `observablehq.config.ts` — `root: "src"`, pages/sidebar nav, theme
  (light default, custom head with fonts + favicon), `preserveExtension: false`.
- Node **22 LTS** for local dev and CI (matches Framework's deploy guide).

---

## 5. Data snapshots — formats and contracts

### 5.1 General rules

- One file per dataset × granularity; **tidy/long format** (one observation per row),
  snake_case columns, UTF-8, `.csv` for tables and `.json` only for nested lookups
  (e.g., HS code → description tree).
- Values in **current US dollars, full precision**; formatting (thousand separators,
  "10⁶ USD" units à la Forum Macau) happens client-side. Never pre-round.
- Every snapshot carries a companion `*.meta.json`: `{generated_at, source_notebook,
  comtrade_extract, flow_basis (direct|mirror|both), units: "USD", period, notes}`.
- File names mirror the existing reports convention: `<scope>_<dataset>_<years>.csv`,
  e.g. `cn_plp_flows_2003-2025.csv`, `angola_trade_balance_2003-2025.csv`.
- Snapshots are regenerated by `export_site_data.py`, which **fails loudly** on empty
  DataFrames (guard against the API preview 500-row cap and silent partial data).

### 5.2 Core snapshot contracts (v1)

**`cn_plp_flows_2003-YYYY.csv`** (D1; same shape for `mo_`, `hk_`, `tw_`)

| column | type | notes |
|---|---|---|
| year | int | |
| partner_code | int | UN M49 |
| partner | string | Portuguese short name |
| exports | number | reporter → partner, USD |
| imports | number | reporter ← partner, USD |
| trade_volume | number | exports + imports |
| balance | number | exports − imports |
| basis | string | `direct` or `mirror` |

**`<country>_trade_balance_2003-YYYY.csv`** (D5)

`year, flow_basis, exports, imports, exports_mirror, imports_mirror, balance, balance_mirror`

**`<country>_top_partners_exports_2003-YYYY.csv`** (D6; `_imports_` variant)

`year, partner_code, partner, value, share_pct, rank, basis`

**`<country>_top_products_exports_HS-AG6_2003-YYYY.csv`** (D7; `_imports_` variant)

`year, hs6, description_pt, value, share_pct, rank, basis`

**`<country>_products_partners_HS-AG6_2003-YYYY.csv`** (D8; plus `_partners_products_`)

`year, hs6, description_pt, partner_code, partner, value, share_pct, basis`

**Reference:** `plp_countries.json` (M49, PT/EN names, flag/ISO3), `hs_ag6_labels.json`.

---

## 6. Site structure and pages

### 6.1 Information architecture (v1)

| Route | Title (PT) | Data | Contents |
|---|---|---|---|
| `/` | China–PLP: comércio em números | D1 | Headline KPIs (latest year volume, balance), hero time-series chart, small-multiples per PLP, links to sections |
| `/china-plp` | Trocas China–PLP | D1 | Interactive explorer: stacked/lines by country; flow toggle (Trocas/Exportações/Importações/Saldo); data table; Forum Macau–style table view; CSV download |
| `/macau`, `/hong-kong`, `/taiwan` | Macau (RAEM) / Hong Kong (RAEHK) / Taiwan (Prov. China)–PLP | D2–D4 | Same explorer pattern; Macau (RAEM) page adds "platform role" narrative comparing Macau (RAEM)'s share vs. China direct. Taiwan-related data pages carry a methodological note: Taiwan (Prov. China) is reported under code 490, "Other Asia, nes", per the [UN Comtrade documentation](https://uncomtrade.org/docs/taiwan-province-of-china-trade-data/) |
| `/perfis/` | Perfis por país | D5–D8 index | Country picker grid (9 PLPs) |
| `/perfis/<pais>` | Perfil: Angola (etc.) | D5–D8 | Trade balance (direct vs mirror), top partners, top products, product×partner explorer — mirrors notebook §1–§3 numbering so readers can cross-reference the READMEs |
| `/metodologia` | Metodologia e fontes | — | UN Comtrade source & API, direct/mirror explanation, CIF/FOB caveat, HS-AG6 aggregation, validation vs Forum Macau tables and WITS, update cadence, how to cite |
| `/dados` | Dados abertos | all | Download page: every snapshot CSV + meta, link to repo and notebooks |

### 6.2 Visual language

- Theme: light, serif display + sans body (Framework theme tokens), palette anchored on
  CPLP/Forum Macau-adjacent blues/greens; categorical palette colorblind-safe (Plot's
  `observable10` default acceptable).
- Every chart: title, unit ("mil milhões USD" where scaled), source line
  ("Fonte: UN Comtrade, extração própria"), and basis badge (directo/espelho).
- Chart types: line (evolution), stacked area/bar (composition by country/product),
  bar ranking (top-N per year), slope/heatmap optional for product×partner (D8),
  KPI `big number` cards on the landing page.
- Per-country views are **grouped into volume tiers** (top 2 / next 3 / rest, by max
  value), each tier rendered as its own chart with its own y-scale — mirroring the
  notebooks' multi-panel figures; a single shared-scale view compresses low-volume
  countries and must not be used.
- Interactions via `Inputs`: country multi-select, year range, flow selector,
  direct/mirror toggle, log-scale toggle for long-tailed values.

### 6.3 Responsive & accessibility

- Mobile-first; charts use `resize` via `Plot.plot({width, ...})` patterns from Framework.
- WCAG-minded: sufficient contrast, text alternatives (figure captions), keyboard-operable
  controls, tables available for every chart's underlying data.

### 6.4 i18n path

v1 Portuguese only. Structure copy so a later `/en/` mirror is possible (all UI strings in
one `components/i18n.js` dictionary from day one — cheap now, expensive to retrofit).

---

## 7. Build & local development

- Prerequisites: Node 22, Python venv from repo root (`venv/`), committed snapshots present.
- `cd site && npm install && npm run dev` → preview at `http://localhost:3000`.
- Regenerate data: `venv/bin/python site/scripts/export_site_data.py` (imports
  `comtradetools`; reuses `cache/`; writes `site/src/data/`; `--countries`,
  `--datasets`, `--check` flags).
- `npm run build` → `site/dist/` (static).
- Lint/format: Framework default (Prettier) for `site/`; Python side stays under
  existing `.flake8`.

---

## 8. Deployment — GitHub Pages

- GitHub Actions as Pages source (per Framework's deploying guide):
  `.github/workflows/deploy.yml` with `actions/configure-pages`,
  `upload-pages-artifact` (path `site/dist`), `deploy-pages`.
- Triggers: `push` to `main` (paths `site/**`), plus `workflow_dispatch`.
  A scheduled data refresh is **deferred to v2** (§4.2).
- Base path: project site at `https://<user>.github.io/cipf-comtrade/` → no config needed
  (Framework emits relative paths by default); if a custom domain is adopted later, keep
  default and add `CNAME`.
- Secrets: none needed in v1. v2 scheduled refresh adds `COMTRADE_API_KEY` repo secret and
  `actions/cache` for the Framework loader cache.
- Branch protection: `main` deploys only after build success; data-refresh PRs reviewed
  before merge (numbers are citable — no unreviewed auto-updates).

---

## 9. Quality, validation, testing

1. **Snapshot parity checks** (`export_site_data.py --check`): recompute D1 totals and
   compare against the Forum Macau quadros already validated in
   `reports/quadros_forum_2003-2023.xlsx` (tolerance: exact for totals; note known
   rounding in Forum's 10⁷/10¹⁰-unit prints).
2. **No-empty / no-partial guards:** snapshot generation aborts on empty DataFrame,
   missing years, or row counts below expectation (mirrors the API 500-row-cap pitfall).
3. **Schema tests:** a small pytest module (`tests/test_site_exports.py`) validates each
   committed snapshot against the §5.2 contracts (columns, dtypes, value ranges,
   `basis ∈ {direct, mirror}`), running offline like the existing suite.
4. **Build gate:** `npm run build` must succeed in CI; Framework fails the build on any
   broken `FileAttachment`.
5. **Manual review checklist** before enabling the site publicly: spot-check 3 countries
   against WITS country snapshots; verify PT labels; verify all downloads.

---

## 10. Performance budget

- Landing page: ≤ 300 KB total data payload (pre-aggregated; no HS-6 raw dumps on `/`).
- Any single page ≤ 1 MB data; larger tables (D8) loaded only on their pages and
  pre-filtered to top-N per year (N=10 default).
- No runtime fetch to external APIs; fonts self-hosted or system stack.

---

## 11. Phased roadmap

| Phase | Scope | Exit criteria |
|---|---|---|
| **0 — Scaffold** | `site/` Framework init, config, theme, deploy.yml live with placeholder page | `github.io` URL serves "em construção" page |
| **1 — Flagship (D1)** | `export_site_data.py` for D1; `/` + `/china-plp` with charts, table, downloads; parity checks vs Forum quadros | Numbers match validated Excel; PT copy reviewed |
| **2 — Platforms (D2–D4)** | Macau (RAEM)/HK (RAEHK)/Taiwan (Prov. China) pages, Macau (RAEM)-platform narrative | Same checks; navigation complete |
| **3 — Country profiles (D5–D8)** | `/perfis/*` for all 9 PLPs, product×partner explorer | Spot-check vs WITS; READMEs cross-linked |
| **4 — Methodology & data page** | `/metodologia`, `/dados`, citation format | Public announcement-ready |
| **5 — v2 candidates** | scheduled data refresh (secret + cache), EN mirror, embeddable charts, per-HS-chapter deep dives (D9) | per-effort specs |

---

## 12. Risks and open questions

| Risk / question | Mitigation / decision needed |
|---|---|
| Stale snapshots (data only as fresh as last local export) | v2 scheduled refresh; show "dados até YYYY" badge on every page |
| Direct vs mirror confusion by casual readers | always label basis; default view = direct with mirror toggle; methodology page |
| HS revisions (descriptions differ across years — known WITS mismatches) | pin HS vintage note per snapshot; keep AG6 aggregation consistent with notebooks |
| Repo size: committing CSV snapshots | fine (estimated ≤ a few MB); keep raw pickle cache gitignored as today |
| **Open:** custom domain (e.g., under an institutional domain) vs `github.io` path | decide before Phase 4 (affects CNAME and absolute links) |
| **Open:** embed selected charts back into Forum Macau/UPM pages? | affects CORS/asset strategy; v2 |

---

## 13. References

- Observable Framework: [What is Framework](https://observablehq.com/framework/what-is-framework) ·
  [Data loaders](https://observablehq.com/framework/data-loaders) ·
  [Deploying](https://observablehq.com/framework/deploying) ·
  [Plot](https://observablehq.com/plot/) · [Inputs](https://github.com/observablehq/inputs)
- Project docs: `AGENTS.md`, `docs/comtradetools.md`, `country_trade_profile_README_EN.md`,
  `cn_plp_import_export_README.md`
- Data source: [UN Comtrade](https://comtradeplus.un.org/) API (key in local `config.ini`)
