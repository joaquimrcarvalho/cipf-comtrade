# China–PLP: comércio em números

Observatório de dados do comércio entre a **China** e os Países de Língua Portuguesa
(PLP) e do papel de **Macau (RAEM)** como plataforma. Dados
[UN Comtrade](https://comtradeplus.un.org/), visualização interativa gerada com
[Observable Framework](https://observablehq.com/framework/) a partir do projeto
[cipf-comtrade](https://github.com/joaquimrcarvalho/cipf-comtrade).

```js
import {formatUSD, usdAxis, pctSigned} from "./components/format.js";
import {kpiCards} from "./components/cards.js";

const flows = await FileAttachment("data/cn_plp_flows_2003-2024.csv").csv({typed: true});
const direct = flows.filter((d) => d.basis === "direct");
const years = Array.from(new Set(direct.map((d) => d.year))).sort(d3.ascending);
const latestYear = years.at(-1);
const latest = direct.filter((d) => d.year === latestYear);
const sum = (m, rows = latest) => d3.sum(rows, (d) => d[m]);
const prev = direct.filter((d) => d.year === latestYear - 1);
const yoy = (sum("trade_volume") - sum("trade_volume", prev)) / sum("trade_volume", prev) * 100;
```

## Trocas China ↔ PLP, ${latestYear}

```js
display(kpiCards(html, [
  {label: "Trocas comerciais", value: formatUSD(sum("trade_volume")),
   sub: `${pctSigned(yoy)} face a ${latestYear - 1}`},
  {label: "Exportações da China", value: formatUSD(sum("exports")), sub: "para os PLP"},
  {label: "Importações da China", value: formatUSD(sum("imports")), sub: "dos PLP"},
  {label: "Saldo comercial", value: formatUSD(sum("balance")), sub: "perspetiva da China"}
]));
```

```js
const totals = d3
  .rollups(direct, (v) => d3.sum(v, (d) => d.trade_volume), (d) => d.year)
  .map(([year, value]) => ({year, value}))
  .sort((a, b) => d3.ascending(a.year, b.year));

display(Plot.plot({
  marginLeft: 75,
  grid: true,
  y: {label: "Trocas comerciais (USD)", tickFormat: usdAxis},
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

<div style="font-size: 0.85rem; color: var(--theme-foreground-muted)">
  Valores reportados pela China (base direta), ${years[0]}–${latestYear} ·
  Fonte: UN Comtrade, extração e análise próprias ·
  <a href="/china-plp">Explorar em detalhe →</a>
</div>

## Secções

| Secção                            | Estado         | Conteúdo                                                                                          |
| ----------------------------------- | -------------- | -------------------------------------------------------------------------------------------------- |
| [Trocas China–PLP](/china-plp)      | ✅ disponível | Exportações, importações, volume de trocas e saldo, 2003–${latestYear}; base direta e espelho |
| [Macau (RAEM)–PLP](/macau)          | ✅ disponível | Trocas de Macau (RAEM) com os PLP e análise do papel de plataforma                                |
| [Hong Kong (RAEHK)–PLP](/hong-kong) | ✅ disponível | Trocas de Hong Kong (RAEHK) com os PLP; base direta e espelho                                     |
| [Perfis por país](/perfis)          | 🚧 fase 3      | Balança, principais parceiros e produtos (HS-AG6) de cada PLP                                     |
| [Metodologia e fontes](/metodologia) | 🚧 fase 4      | Fontes, direto vs. espelho, validação, como citar                                                |
| [Dados abertos](/dados)              | 🚧 fase 4      | Descarregamento de todos os conjuntos de dados                                                     |

## Fonte e validação

Todos os valores provêm da base de dados [UN Comtrade](https://comtradeplus.un.org/),
obtidos via API com o módulo
[`comtradetools.py`](https://github.com/joaquimrcarvalho/cipf-comtrade) e validados
contra os quadros publicados anualmente pelo
[Fórum para a Cooperação Económica e Comercial entre a China e os Países de Língua
Portuguesa (Fórum Macau)](https://www.forumchinaplp.org.mo/), desde 2016.
