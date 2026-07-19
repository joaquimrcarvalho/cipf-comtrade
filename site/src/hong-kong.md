# Trocas Hong Kong (RAEHK)–PLP

Evolução das trocas comerciais entre **Hong Kong (RAEHK)** e os Países de Língua
Portuguesa (PLP), em USD correntes. Os valores *diretos* são reportados por Hong Kong;
os valores *espelho* são inferidos dos reportes dos parceiros — as duas bases diferem
por CIF/FOB, reexportações e falhas de reporte, e ambas são apresentadas.

```js
import {formatUSD, usdInt, usdAxis} from "./components/format.js";
import {L, MEASURES, MEASURE_LABEL} from "./components/i18n.js";
import {kpiCards} from "./components/cards.js";

const flows = await FileAttachment("data/hk_plp_flows_2003-2024.csv").csv({typed: true});
const meta = await FileAttachment("data/hk_plp_flows_2003-2024.meta.json").json();
```

```js
const years = Array.from(new Set(flows.map((d) => d.year))).sort(d3.ascending);
const latestYear = years.at(-1);
const latest = flows.filter((d) => d.year === latestYear && d.basis === "direct");
const sumLatest = (m) => d3.sum(latest, (d) => d[m]);
```

<div class="note" style="font-size: 0.85rem; color: var(--theme-foreground-muted)">
  Dados de ${years[0]} a ${latestYear} · atualizado em ${meta.generated_at.slice(0, 10)}
</div>

## ${latestYear} em síntese (base direta)

```js
display(kpiCards(html, [
  {label: "Trocas comerciais", value: formatUSD(sumLatest("trade_volume")), sub: `Hong Kong (RAEHK) ↔ PLP, ${latestYear}`},
  {label: "Exportações de Hong Kong", value: formatUSD(sumLatest("exports")), sub: "para os PLP"},
  {label: "Importações de Hong Kong", value: formatUSD(sumLatest("imports")), sub: "dos PLP"},
  {label: "Saldo comercial", value: formatUSD(sumLatest("balance")), sub: "perspetiva de Hong Kong"}
]));
```

## Explorar

```js
const measure = view(Inputs.radio(MEASURES, {label: L.medida, value: "trade_volume"}));
const basis = view(Inputs.radio(
  new Map([
    ["Reportado por Hong Kong (RAEHK)", "direct"],
    ["Espelho (reportado pelos PLP)", "mirror"]
  ]),
  {label: L.base, value: "direct"}
));
const logScale = view(Inputs.toggle({label: L.logScale, value: false}));
```

```js
const data = flows.filter((d) => d.basis === basis);
const isLog = logScale && measure !== "balance"; // saldo tem valores negativos
const totals = d3
  .rollups(data, (v) => d3.sum(v, (d) => d[measure]), (d) => d.year)
  .map(([year, value]) => ({year, value}))
  .sort((a, b) => d3.ascending(a.year, b.year));
const yLabel = `${MEASURE_LABEL[measure]} (USD)`;
```

### Total Hong Kong (RAEHK) ↔ PLP

```js
display(Plot.plot({
  marginLeft: 75,
  grid: true,
  y: {type: isLog ? "log" : "linear", label: yLabel, tickFormat: usdAxis},
  x: {label: null, tickFormat: "d"},
  marks: [
    ...(isLog ? [] : [Plot.ruleY([0])]),
    Plot.areaY(totals, {x: "year", y: "value", fillOpacity: 0.12}),
    Plot.line(totals, {x: "year", y: "value", strokeWidth: 2, tip: {
      format: {x: "d", y: (v) => formatUSD(v)}
    }}),
    Plot.dot(totals, {x: "year", y: "value", r: 2})
  ]
}));
```

### Por país

```js
// Agrupar por ordem de grandeza (top 2, seguintes 3, restantes) — ver china-plp.md
const byMax = d3
  .rollups(data, (v) => d3.max(v, (d) => Math.abs(d[measure])), (d) => d.partner)
  .map(([partner, maxAbs]) => ({partner, maxAbs}))
  .sort((a, b) => d3.descending(a.maxAbs, b.maxAbs));
const groups = [byMax.slice(0, 2), byMax.slice(2, 5), byMax.slice(5)].filter((g) => g.length > 0);
const groupTitles = ["Maiores volumes", "Volumes intermédios", "Menores volumes"];
const colorDomain = Array.from(new Set(flows.map((d) => d.partner)));
const colorOf = new Map(colorDomain.map((p, i) => [p, d3.schemeObservable10[i]]));
```

```js
display(html`${groups.map((g, i) => {
  const members = new Set(g.map((d) => d.partner));
  const gdata = data.filter((d) => members.has(d.partner));
  const gmembers = g.map((d) => d.partner);
  const chart = Plot.plot({
    marginLeft: 75,
    grid: true,
    y: {type: isLog ? "log" : "linear", label: yLabel, tickFormat: usdAxis},
    x: {label: null, tickFormat: "d"},
    color: {domain: gmembers, range: gmembers.map((p) => colorOf.get(p)), legend: true},
    marks: [
      ...(isLog ? [] : [Plot.ruleY([0])]),
      Plot.line(gdata, {x: "year", y: measure, stroke: "partner", strokeWidth: 1.8,
        tip: {format: {x: "d", y: (v) => formatUSD(v)}}}),
      Plot.dot(gdata, {x: "year", y: measure, fill: "partner", r: 1.8})
    ]
  });
  return html`<h4 style="margin-top: 1.5rem;">${groupTitles[i]} · ${gmembers.join(", ")}</h4>${chart}`;
})}`);
```

<div style="font-size: 0.85rem; color: var(--theme-foreground-muted)">
  ${L.fonte} · base: ${basis === "direct" ? "valores reportados por Hong Kong (RAEHK)" : "valores reportados pelos parceiros (espelho)"} ·
  gráficos agrupados por ordem de grandeza, cada grupo com a sua escala.
</div>

## Tabela

```js
const tableRows = data.map((d) => ({
  Ano: d.year,
  País: d.partner,
  Exportações: d.exports,
  Importações: d.imports,
  Trocas: d.trade_volume,
  Saldo: d.balance
}));
display(Inputs.table(tableRows, {
  rows: 14,
  sort: "Ano",
  reverse: true,
  format: {
    Ano: (v) => String(v),
    Exportações: usdInt,
    Importações: usdInt,
    Trocas: usdInt,
    Saldo: usdInt
  }
}));
```

## Descarregar

```js
display(html`<p>
  <a href="${FileAttachment("data/hk_plp_flows_2003-2024.csv").href}" download>${L.downloadCSV}</a> ·
  <a href="${FileAttachment("data/hk_plp_flows_2003-2024.meta.json").href}" download>${L.downloadMeta}</a>
</p>`);
```

---

Dados de origem: bloco de notas `hk_plp_import_export.ipynb` do projeto
[cipf-comtrade](https://github.com/joaquimrcarvalho/cipf-comtrade).
Metodologia completa em [Metodologia e fontes](/metodologia).
