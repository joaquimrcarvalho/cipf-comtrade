# Trocas China–PLP

Evolução das trocas comerciais entre a **China** e os nove Países de Língua Portuguesa
(PLP), em USD correntes. Os valores *diretos* são reportados pela China; os valores
*espelho* são inferidos dos reportes dos parceiros (as importações que declaram da China
e as exportações que declaram para a China) — as duas bases diferem por CIF/FOB e falhas
de reporte, e ambas são apresentadas.

```js
import {formatUSD, usdInt, usdAxis} from "./components/format.js";
import {L, MEASURES, MEASURE_LABEL} from "./components/i18n.js";
import {kpiCards} from "./components/cards.js";

const flows = await FileAttachment("data/cn_plp_flows_2003-2024.csv").csv({typed: true});
const meta = await FileAttachment("data/cn_plp_flows_2003-2024.meta.json").json();
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
  {label: "Trocas comerciais", value: formatUSD(sumLatest("trade_volume")), sub: `China ↔ PLP, ${latestYear}`},
  {label: "Exportações da China", value: formatUSD(sumLatest("exports")), sub: "para os PLP"},
  {label: "Importações da China", value: formatUSD(sumLatest("imports")), sub: "dos PLP"},
  {label: "Saldo comercial", value: formatUSD(sumLatest("balance")), sub: "perspetiva da China"}
]));
```

## Explorar

```js
const measure = view(Inputs.radio(MEASURES, {label: L.medida, value: "trade_volume"}));
const basis = view(Inputs.radio(
  new Map([
    ["Reportado pela China", "direct"],
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

### Total China ↔ PLP

```js
display(Plot.plot({
  marginLeft: 75,
  grid: true,
  y: {type: isLog ? "log" : "linear", label: yLabel, tickFormat: usdAxis},
  x: {label: null, tickFormat: "d"},
  marks: [
    Plot.ruleY([0]),
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
display(Plot.plot({
  height: 620,
  marginLeft: 75,
  grid: true,
  y: {type: isLog ? "log" : "linear", label: yLabel, tickFormat: usdAxis},
  x: {label: null, tickFormat: "d"},
  fy: {label: null},
  marks: [
    Plot.ruleY([0]),
    Plot.line(data, {
      x: "year", y: measure, fy: "partner",
      stroke: "#2a6f97", strokeWidth: 1.5,
      tip: {format: {x: "d", y: (v) => formatUSD(v), fy: true}}
    }),
    Plot.dot(data, {x: "year", y: measure, fy: "partner", r: 1.5, fill: "#2a6f97"})
  ]
}));
```

<div style="font-size: 0.85rem; color: var(--theme-foreground-muted)">
  ${L.fonte} · base: ${basis === "direct" ? "valores reportados pela China" : "valores reportados pelos parceiros (espelho)"} ·
  escalas dos painéis partilhadas para comparabilidade.
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
  <a href="${FileAttachment("data/cn_plp_flows_2003-2024.csv").href}" download>${L.downloadCSV}</a> ·
  <a href="${FileAttachment("data/cn_plp_flows_2003-2024.meta.json").href}" download>${L.downloadMeta}</a>
</p>`);
```

---

**Validação:** estes valores (base direta) reproduzem os quadros publicados pelo
[Fórum Macau](https://www.forumchinaplp.org.mo/) — verificação automática em
`site/scripts/export_site_data.py --check`. Metodologia completa em
[Metodologia e fontes](/metodologia).
