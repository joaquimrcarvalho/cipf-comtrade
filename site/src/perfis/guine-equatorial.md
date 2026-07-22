# Perfil: Guiné Equatorial

Perfil comercial de **Guiné Equatorial** (2003–2024), espelhando a estrutura do bloco de
notas `country_trade_profile.ipynb`: **1.** balança comercial (base direta vs. espelho),
**2.** exportações e **3.** importações — principais parceiros, principais produtos
(HS-AG6) e quem compra/fornece o quê. Valores em USD correntes.

```js
import {formatUSD, usdInt, usdAxis, pct} from "../components/format.js";
import {L} from "../components/i18n.js";
import {kpiCards} from "../components/cards.js";
import {volumeCompareChart, balanceChart, rankBarChart, evolutionChart,
        productPartnersChart, competitionChart, pseudoPartnerNote,
        trunc} from "../components/profile.js";

const balance = await FileAttachment("../data/guine-equatorial_trade_balance_2003-2024.csv").csv({typed: true});
const topPartX = await FileAttachment("../data/guine-equatorial_top_partners_exports_2003-2024.csv").csv({typed: true});
const topPartM = await FileAttachment("../data/guine-equatorial_top_partners_imports_2003-2024.csv").csv({typed: true});
const topProdX = await FileAttachment("../data/guine-equatorial_top_products_exports_HS-AG6_2003-2024.csv").csv({typed: true});
const topProdM = await FileAttachment("../data/guine-equatorial_top_products_imports_HS-AG6_2003-2024.csv").csv({typed: true});
const d8x = await FileAttachment("../data/guine-equatorial_products_partners_HS-AG6_2003-2024.csv").csv({typed: true});
const d8m = await FileAttachment("../data/guine-equatorial_partners_products_HS-AG6_2003-2024.csv").csv({typed: true});
const meta = await FileAttachment("../data/guine-equatorial_profile_2003-2024.meta.json").json();
```

```js
const years = Array.from(new Set(balance.map((d) => d.year))).sort(d3.ascending);
const latestYear = years.at(-1);
const latest = balance.filter((d) => d.year === latestYear && d.basis === "direct");
const latestMirror = balance.filter((d) => d.year === latestYear && d.basis === "mirror");
const at = (rows, m) => rows.length ? rows[0][m] : null;
const orEmpty = (rows, node) => rows.length
  ? node
  : html`<p style="font-size: 0.85rem; color: var(--theme-foreground-muted)"><em>Sem dados para esta seleção.</em></p>`;
const rankTable = (rows, nameCol, nameLabel) => Inputs.table(
  rows.map((d) => ({[nameLabel]: d.hs6 ? `${d.hs6} — ${trunc(d[nameCol], 60)}` : d[nameCol],
                    Valor: d.value,
                    "Quota (%)": d.share_pct, "Pos.": d.rank})),
  {rows: 10, format: {Valor: usdInt,
                      "Quota (%)": (v) => pct(v), "Pos.": (v) => String(v)}});
```

<div class="note" style="font-size: 0.85rem; color: var(--theme-foreground-muted)">
  Dados de ${years[0]} a ${latestYear} · atualizado em ${meta.generated_at.slice(0, 10)} ·
  valores <em>diretos</em> reportados por Guiné Equatorial; valores <em>espelho</em> reportados
  pelos parceiros (soma exclui o agregado «Mundo» para evitar dupla contagem).
</div>

```js
const basis = view(Inputs.radio(
  new Map([
    ["Reportado por Guiné Equatorial (direto)", "direct"],
    ["Reportado pelos parceiros (espelho)", "mirror"]
  ]),
  {label: L.base, value: "direct"}
));
const year = view(Inputs.range([2003, 2024], {step: 1, value: 2024, label: L.ano}));
```

## ${latestYear} em síntese (base direta)

```js
display(kpiCards(html, [
  {label: "Volume de trocas", value: formatUSD(at(latest, "trade_volume")),
   sub: `Guiné Equatorial ↔ mundo, ${latestYear}`},
  {label: "Exportações", value: formatUSD(at(latest, "exports")), sub: "Guiné Equatorial → mundo"},
  {label: "Importações", value: formatUSD(at(latest, "imports")), sub: "mundo → Guiné Equatorial"},
  {label: "Saldo comercial", value: formatUSD(at(latest, "balance")), sub: "perspetiva de Guiné Equatorial"}
]));
```

<div style="font-size: 0.85rem; color: var(--theme-foreground-muted)">
  Em base espelho, o volume de ${latestYear} foi
  ${formatUSD(at(latestMirror, "trade_volume"))} — divergências face à base direta são
  esperadas (CIF/FOB, falhas de reporte) e visíveis no gráfico seguinte.
</div>

## 1. Balança comercial — direto vs. espelho

```js
display(volumeCompareChart(Plot, d3, balance, {usdAxis, formatUSD}));
```

### Saldo comercial (base: ${basis === "direct" ? "direta" : "espelho"})

```js
display(balanceChart(Plot, d3, balance, basis, {usdAxis, formatUSD}));
```

## 2. Exportações de Guiné Equatorial

### 2.1 Principais clientes — top 10 em ${year}

```js
const partX = topPartX.filter((d) => d.year === year && d.basis === basis);
display(orEmpty(partX, rankBarChart(Plot, d3, partX, "partner", {usdAxis, formatUSD, pct})));
```

```js
display(orEmpty(partX, rankTable(partX, "partner", "Parceiro")));
```

${pseudoPartnerNote(html, partX, "partner_code")}

Evolução dos 5 maiores clientes no período (base ${basis === "direct" ? "direta" : "espelho"}):

```js
const partXall = topPartX.filter((d) => d.basis === basis);
display(orEmpty(partXall, evolutionChart(Plot, d3, partXall, "partner", 5, {usdAxis, formatUSD})));
```

### 2.2 Principais produtos exportados (HS-AG6) — top 10 em ${year}

```js
const prodX = topProdX.filter((d) => d.year === year && d.basis === basis);
display(orEmpty(prodX, rankBarChart(Plot, d3, prodX, "description_pt", {usdAxis, formatUSD, pct})));
```

```js
display(orEmpty(prodX, rankTable(prodX, "description_pt", "Produto")));
```

Evolução dos 5 principais produtos no período:

```js
const prodXall = topProdX.filter((d) => d.basis === basis);
display(orEmpty(prodXall, evolutionChart(Plot, d3, prodXall, "description_pt", 5, {usdAxis, formatUSD})));
```

### 2.3 Quem compra o quê (produto × parceiro)

```js
const prodOptionsX = new Map(
  d3.rollups(d8x, (v) => d3.sum(v, (d) => d.value), (d) => d.hs6)
    .sort((a, b) => d3.descending(a[1], b[1]))
    .map(([hs6, total]) => {
      const desc = d8x.find((d) => d.hs6 === hs6)?.description_pt ?? hs6;
      return [`${hs6} — ${trunc(desc, 38)}`, hs6];
    })
);
const productX = view(Inputs.select(prodOptionsX, {label: "Produto (HS6)"}));
```

```js
const d8sel = d8x.filter((d) => d.hs6 === productX && d.basis === basis);
display(orEmpty(d8sel, productPartnersChart(Plot, d3, d8sel, {usdAxis, formatUSD})));
```

<div style="font-size: 0.85rem; color: var(--theme-foreground-muted)">
  Linhas: principais compradores do produto selecionado (quota no total do produto em
  cada ano, base ${basis === "direct" ? "direta" : "espelho"}). A lista cobre os
  25 principais produtos de todo o período — por isso tem mais entradas
  do que a tabela de §2.2, que mostra apenas o top 10 de cada ano.
</div>

${pseudoPartnerNote(html, d8sel, "partner_code")}



## 3. Importações de Guiné Equatorial

### 3.1 Principais fornecedores — top 10 em ${year}

```js
const partM = topPartM.filter((d) => d.year === year && d.basis === basis);
display(orEmpty(partM, rankBarChart(Plot, d3, partM, "partner", {usdAxis, formatUSD, pct})));
```

```js
display(orEmpty(partM, rankTable(partM, "partner", "Parceiro")));
```

${pseudoPartnerNote(html, partM, "partner_code")}

Evolução dos 5 maiores fornecedores no período (base ${basis === "direct" ? "direta" : "espelho"}):

```js
const partMall = topPartM.filter((d) => d.basis === basis);
display(orEmpty(partMall, evolutionChart(Plot, d3, partMall, "partner", 5, {usdAxis, formatUSD})));
```

### 3.2 Principais produtos importados (HS-AG6) — top 10 em ${year}

```js
const prodM = topProdM.filter((d) => d.year === year && d.basis === basis);
display(orEmpty(prodM, rankBarChart(Plot, d3, prodM, "description_pt", {usdAxis, formatUSD, pct})));
```

```js
display(orEmpty(prodM, rankTable(prodM, "description_pt", "Produto")));
```

Evolução dos 5 principais produtos no período:

```js
const prodMall = topProdM.filter((d) => d.basis === basis);
display(orEmpty(prodMall, evolutionChart(Plot, d3, prodMall, "description_pt", 5, {usdAxis, formatUSD})));
```

### 3.3 Quem fornece o quê (parceiro × produto)

```js
const prodOptionsM = new Map(
  d3.rollups(d8m, (v) => d3.sum(v, (d) => d.value), (d) => d.hs6)
    .sort((a, b) => d3.descending(a[1], b[1]))
    .map(([hs6, total]) => {
      const desc = d8m.find((d) => d.hs6 === hs6)?.description_pt ?? hs6;
      return [`${hs6} — ${trunc(desc, 38)}`, hs6];
    })
);
const productM = view(Inputs.select(prodOptionsM, {label: "Produto (HS6)"}));
```

```js
const d8selM = d8m.filter((d) => d.hs6 === productM && d.basis === basis);
display(orEmpty(d8selM, productPartnersChart(Plot, d3, d8selM, {usdAxis, formatUSD})));
```

<div style="font-size: 0.85rem; color: var(--theme-foreground-muted)">
  ${L.fonte} · base: ${basis === "direct" ? "valores reportados por Guiné Equatorial" : "valores reportados pelos parceiros (espelho)"} ·
  top 10 por ano; produto × parceiro limitado aos 25 principais
  produtos de todo o período (8 parceiros por produto/ano) — daí a
  lista de §3.3 ter mais entradas do que a tabela de §3.2.
</div>

${pseudoPartnerNote(html, d8selM, "partner_code")}



## Descarregar

```js
display(html`<p>
  <a href="${FileAttachment("../data/guine-equatorial_trade_balance_2003-2024.csv").href}" download>Balança comercial (CSV)</a> ·
  <a href="${FileAttachment("../data/guine-equatorial_top_partners_exports_2003-2024.csv").href}" download>Clientes (CSV)</a> ·
  <a href="${FileAttachment("../data/guine-equatorial_top_partners_imports_2003-2024.csv").href}" download>Fornecedores (CSV)</a> ·
  <a href="${FileAttachment("../data/guine-equatorial_top_products_exports_HS-AG6_2003-2024.csv").href}" download>Produtos exportados (CSV)</a> ·
  <a href="${FileAttachment("../data/guine-equatorial_top_products_imports_HS-AG6_2003-2024.csv").href}" download>Produtos importados (CSV)</a> ·
  <a href="${FileAttachment("../data/guine-equatorial_products_partners_HS-AG6_2003-2024.csv").href}" download>Produto × parceiro (CSV)</a> ·
  <a href="${FileAttachment("../data/guine-equatorial_partners_products_HS-AG6_2003-2024.csv").href}" download>Parceiro × produto (CSV)</a> ·
  <a href="${FileAttachment("../data/guine-equatorial_competition_exports_HS-AG6_2003-2024.csv").href}" download>Concorrência nos clientes (CSV)</a> ·
  <a href="${FileAttachment("../data/guine-equatorial_competition_imports_HS-AG6_2003-2024.csv").href}" download>Concorrência pelos fornecedores (CSV)</a> ·
  <a href="${FileAttachment("../data/guine-equatorial_profile_2003-2024.meta.json").href}" download>${L.downloadMeta}</a>
</p>`);
```

---

Dados de origem: bloco de notas `country_trade_profile.ipynb` do projeto
[cipf-comtrade](https://github.com/joaquimrcarvalho/cipf-comtrade) (numeração das
secções 1–3 paralela à do bloco de notas). Metodologia completa em
[Metodologia e fontes](/metodologia) · outros países em [Perfis por país](/perfis).
