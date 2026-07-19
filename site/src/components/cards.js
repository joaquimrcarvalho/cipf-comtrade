// KPI card grid (big numbers) used on landing and explorer pages.
// values: [{label, value, sub}] — value already formatted.
// `html` must be passed in from the page code block (htl template tag),
// so the returned value is a real DOM node, not an escaped string.
export function kpiCards(html, values) {
  return html`<div style="display: flex; flex-wrap: wrap; gap: 0.75rem; margin: 1rem 0 1.5rem 0;">${values.map((d) => html`
    <div style="background: var(--theme-background-alt); border-radius: 8px; padding: 0.9rem 1.1rem; flex: 1 1 160px;">
      <div style="font-size: 0.8rem; color: var(--theme-foreground-muted);">${d.label}</div>
      <div style="font-size: 1.5rem; font-weight: 600; margin: 0.15rem 0;">${d.value}</div>
      <div style="font-size: 0.75rem; color: var(--theme-foreground-faint);">${d.sub ?? ""}</div>
    </div>`)}
  </div>`;
}
