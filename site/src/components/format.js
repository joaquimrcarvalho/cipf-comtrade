// Number/USD formatting helpers for the site (pt-PT conventions).
// Spec: docs/SITE_SPECS.md §5.1 — values stored full-precision USD, formatted client-side.
// Uses Intl.NumberFormat only (no external imports) so the module always resolves.
const nf0 = new Intl.NumberFormat("pt-PT", {maximumFractionDigits: 0});
const nf1 = new Intl.NumberFormat("pt-PT", {minimumFractionDigits: 1, maximumFractionDigits: 1});

export const usdInt = (v) =>
  v == null || Number.isNaN(v) ? "—" : nf0.format(v);

// "12,3 mil M USD" / "456,7 M USD" / "123 456 USD"
export function formatUSD(v) {
  if (v == null || Number.isNaN(v)) return "—";
  const a = Math.abs(v);
  if (a >= 1e9) return `${nf1.format(v / 1e9)} mil M USD`;
  if (a >= 1e6) return `${nf1.format(v / 1e6)} M USD`;
  return `${nf0.format(v)} USD`;
}

// Compact axis tick version (no "USD" suffix): "12 mil M" / "456 M" / "12 mil"
export function usdAxis(v) {
  const a = Math.abs(v);
  if (a >= 1e9) return `${nf0.format(v / 1e9)} mil M`;
  if (a >= 1e6) return `${nf0.format(v / 1e6)} M`;
  if (a >= 1e3) return `${nf0.format(v / 1e3)} mil`;
  return nf0.format(v);
}

const pctFmt = new Intl.NumberFormat("pt-PT", {minimumFractionDigits: 1, maximumFractionDigits: 1});
const pctSignedFmt = new Intl.NumberFormat("pt-PT", {
  minimumFractionDigits: 1, maximumFractionDigits: 1, signDisplay: "always"
});

export const pct = (v) =>
  v == null || Number.isNaN(v) ? "—" : `${pctFmt.format(v)}%`;

export const pctSigned = (v) =>
  v == null || Number.isNaN(v) ? "—" : `${pctSignedFmt.format(v)}%`;
