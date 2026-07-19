// KPI card grid (big numbers) used on landing and explorer pages.
// values: [{label, value, sub}] — value already formatted.
export function kpiCards(values) {
  const cards = values
    .map(
      (d) => `
    <div style="background: var(--theme-background-alt); border-radius: 8px; padding: 0.9rem 1.1rem; flex: 1 1 160px;">
      <div style="font-size: 0.8rem; color: var(--theme-foreground-muted)">${d.label}</div>
      <div style="font-size: 1.5rem; font-weight: 600; margin: 0.15rem 0">${d.value}</div>
      <div style="font-size: 0.75rem; color: var(--theme-foreground-faint)">${d.sub ?? ""}</div>
    </div>`
    )
    .join("");
  return `<div style="display: flex; flex-wrap: wrap; gap: 0.75rem; margin: 1rem 0 1.5rem 0">${cards}</div>`;
}
