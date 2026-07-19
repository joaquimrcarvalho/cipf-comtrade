// Number/USD formatting helpers for the site (pt-PT conventions).
// Spec: docs/SITE_SPECS.md §5.1 — values stored full-precision USD, formatted client-side.
import {format, formatDefaultLocale} from "d3";

formatDefaultLocale({
  decimal: ",",
  thousands: " ", // espaço fino como separador de milhares
  grouping: [3],
  currency: ["", ""]
});

export const usdInt = (v) =>
  v == null || Number.isNaN(v) ? "—" : format(",.0f")(v);

// "12,3 mil M USD" / "456,7 M USD" / "123 456 USD"
export function formatUSD(v) {
  if (v == null || Number.isNaN(v)) return "—";
  const a = Math.abs(v);
  if (a >= 1e9) return `${format(",.1f")(v / 1e9)} mil M USD`;
  if (a >= 1e6) return `${format(",.1f")(v / 1e6)} M USD`;
  return `${format(",.0f")(v)} USD`;
}

// Compact axis tick version (no "USD" suffix): "12 mil M" / "456 M"
export function usdAxis(v) {
  const a = Math.abs(v);
  if (a >= 1e9) return `${format(",.0f")(v / 1e9)} mil M`;
  if (a >= 1e6) return `${format(",.0f")(v / 1e6)} M`;
  if (a >= 1e3) return `${format(",.0f")(v / 1e3)} mil`;
  return format(",.0f")(v);
}

export const pct = (v, digits = 1) =>
  v == null || Number.isNaN(v) ? "—" : `${format(`,.${digits}f`)(v)}%`;
