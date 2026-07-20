// Chart builders for the /perfis/<pais> country-profile pages (D5–D8).
// Spec: docs/SITE_SPECS.md §6 (visual language).
//
// Dependency-free BY DESIGN: Plot, d3 and Inputs are passed in by the page
// code blocks (where they are implicit globals). This keeps the module
// resolvable in every context — see the project's Observable Framework notes.

export const trunc = (s, n = 44) =>
  s == null ? "" : s.length > n ? `${s.slice(0, n - 1)}…` : s;

const BASIS_LABEL = {direct: "Direto", mirror: "Espelho"};

// Unique series identity + label. Different HS6 products can share the same
// truncated description ("Vehicle parts and accessories; n.e.c. in he…"),
// which merged several series into one jagged line — so product rows are
// keyed by their hs6 code, prefixed into the label (notebook style).
// Partner rows (no hs6) keep their plain name.
const rowId = (d, key) =>
  d.hs6 != null && d.hs6 !== "" ? String(d.hs6) : String(d[key]);
const rowLabel = (d, key, n = 34) =>
  d.hs6 != null && d.hs6 !== "" ? `${d.hs6} — ${trunc(d[key], n)}` : trunc(d[key]);

// Stable categorical colors per series key (same palette as the explorers).
function colorScale(d3, keys) {
  const domain = Array.from(new Set(keys));
  const range = domain.map((_, i) => d3.schemeObservable10[i % 10]);
  return {domain, range};
}

// §1 — trade volume, direct vs mirror (the notebook's core comparison).
export function volumeCompareChart(Plot, d3, d5, {usdAxis, formatUSD}) {
  const data = d5.map((d) => ({...d, base: BASIS_LABEL[d.basis]}));
  const color = colorScale(d3, ["Direto", "Espelho"]);
  return Plot.plot({
    marginLeft: 75,
    grid: true,
    y: {label: "Volume de trocas (USD)", tickFormat: usdAxis},
    x: {label: null, tickFormat: "d"},
    color: {...color, legend: true},
    marks: [
      Plot.ruleY([0]),
      Plot.line(data, {x: "year", y: "trade_volume", stroke: "base",
        strokeWidth: 2, tip: {format: {x: "d", y: (v) => formatUSD(v)}}}),
      Plot.dot(data, {x: "year", y: "trade_volume", fill: "base", r: 1.8})
    ]
  });
}

// §1 — trade balance by year for the selected basis (green/red bars).
export function balanceChart(Plot, d3, d5, basis, {usdAxis, formatUSD}) {
  const data = d5.filter((d) => d.basis === basis);
  return Plot.plot({
    marginLeft: 75,
    grid: true,
    y: {label: "Saldo comercial (USD)", tickFormat: usdAxis},
    x: {label: null, tickFormat: "d"},
    marks: [
      Plot.ruleY([0]),
      Plot.barY(data, {x: "year", y: "balance",
        fill: (d) => (d.balance >= 0 ? "#2ca02c" : "#d62728"),
        tip: {format: {x: "d", y: (v) => formatUSD(v)}}})
    ]
  });
}

// §2/§3 — top-N ranking for a single year (horizontal bars, share in tip).
// rows: D6/D7 entries already filtered to (year, basis); `key` is the label
// column ("partner" or "description_pt").
export function rankBarChart(Plot, d3, rows, key, {usdAxis, formatUSD, pct}) {
  const data = [...rows].sort((a, b) => d3.descending(a.value, b.value))
    .map((d) => ({...d, _label: rowLabel(d, key, 30)}));
  return Plot.plot({
    marginLeft: 240,
    height: Math.max(220, data.length * 30),
    grid: true,
    x: {label: "USD", tickFormat: usdAxis},
    y: {label: null},
    marks: [
      Plot.barX(data, {y: "_label", x: "value", fill: "#4269d0",
        sort: {y: "-x"},
        tip: {format: {y: true, x: (v) => formatUSD(v)}}}),
      Plot.text(data, {y: "_label", x: "value",
        text: (d) => pct(d.share_pct), dx: 4, textAnchor: "start",
        fill: "currentColor", fontSize: 10})
    ]
  });
}

// §2/§3 — evolution lines for the all-time top-N keys of a D6/D7 dataset.
// rows: full D6/D7 frame (one basis already selected); `key` as above.
// Series identity is the HS6 code (product rows) so that products whose
// truncated descriptions collide stay separate lines.
export function evolutionChart(Plot, d3, rows, key, topN, {usdAxis, formatUSD}) {
  const totals = d3.rollups(rows, (v) => d3.sum(v, (d) => d.value),
    (d) => rowId(d, key));
  const topIds = totals.sort((a, b) => d3.descending(a[1], b[1])).slice(0, topN)
    .map(([k]) => k);
  const data = rows.filter((d) => topIds.includes(rowId(d, key)))
    .map((d) => ({...d, _series: rowLabel(d, key)}))
    .sort((a, b) => d3.ascending(a._series, b._series) || d3.ascending(a.year, b.year));
  const color = colorScale(d3, data.map((d) => d._series));
  return Plot.plot({
    marginLeft: 75,
    grid: true,
    y: {label: "USD", tickFormat: usdAxis},
    x: {label: null, tickFormat: "d"},
    color: {...color, legend: true},
    marks: [
      Plot.ruleY([0]),
      Plot.line(data, {x: "year", y: "value", stroke: "_series",
        strokeWidth: 1.8, tip: {format: {x: "d", y: (v) => formatUSD(v)}}}),
      Plot.dot(data, {x: "year", y: "value", fill: "_series", r: 1.6})
    ]
  });
}

// §2.3/§3.3 — for one product (D8 rows already filtered to hs6 + basis):
// partner lines over the years.
export function productPartnersChart(Plot, d3, rows, {usdAxis, formatUSD}) {
  const totals = d3.rollups(rows, (v) => d3.sum(v, (d) => d.value), (d) => d.partner);
  const top = totals.sort((a, b) => d3.descending(a[1], b[1])).map(([k]) => k);
  const color = colorScale(d3, top);
  return Plot.plot({
    marginLeft: 75,
    grid: true,
    y: {label: "USD", tickFormat: usdAxis},
    x: {label: null, tickFormat: "d"},
    color: {...color, legend: true},
    marks: [
      Plot.ruleY([0]),
      Plot.line(rows, {x: "year", y: "value", stroke: "partner",
        strokeWidth: 1.8, tip: {format: {x: "d", y: (v) => formatUSD(v)}}}),
      Plot.dot(rows, {x: "year", y: "value", fill: "partner", r: 1.6})
    ]
  });
}
