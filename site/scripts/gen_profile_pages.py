#!/usr/bin/env python3
"""Generate the /perfis/<slug>.md country-profile pages for the site.

One template, nine thin pages (Angola … Timor-Leste); each page loads its
D5–D8 snapshots from site/src/data/ and renders charts via components/profile.js.
Regenerate after changing the template:

    venv/bin/python site/scripts/gen_profile_pages.py

The generated files are committed to the repo (Observable Framework has no
build-time codegen hook for pages; keep them in sync through this script).
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGES_DIR = REPO_ROOT / "site" / "src" / "perfis"

# slug -> Portuguese country name (must match export_profiles.COUNTRIES).
COUNTRIES = {
    "angola": "Angola",
    "brasil": "Brasil",
    "cabo-verde": "Cabo Verde",
    "guine-bissau": "Guiné-Bissau",
    "guine-equatorial": "Guiné Equatorial",
    "mocambique": "Moçambique",
    "portugal": "Portugal",
    "sao-tome-e-principe": "São Tomé e Príncipe",
    "timor-leste": "Timor-Leste",
}

START, END = 2003, 2024
SPAN = f"{START}-{END}"

TEMPLATE = """# Perfil: __NAME__

Perfil comercial de **__NAME__** (__START__–__END__), espelhando a estrutura do bloco de
notas `country_trade_profile.ipynb`: **1.** balança comercial (base direta vs. espelho),
**2.** exportações e **3.** importações — principais parceiros, principais produtos
(HS-AG6) e quem compra/fornece o quê. Valores em USD correntes.

```js
import {formatUSD, usdInt, usdAxis, pct} from "../components/format.js";
import {L} from "../components/i18n.js";
import {kpiCards} from "../components/cards.js";
import {volumeCompareChart, balanceChart, rankBarChart, evolutionChart,
        productPartnersChart, competitionChart, trunc} from "../components/profile.js";

const balance = await FileAttachment("../data/__SLUG___trade_balance___SPAN__.csv").csv({typed: true});
const topPartX = await FileAttachment("../data/__SLUG___top_partners_exports___SPAN__.csv").csv({typed: true});
const topPartM = await FileAttachment("../data/__SLUG___top_partners_imports___SPAN__.csv").csv({typed: true});
const topProdX = await FileAttachment("../data/__SLUG___top_products_exports_HS-AG6___SPAN__.csv").csv({typed: true});
const topProdM = await FileAttachment("../data/__SLUG___top_products_imports_HS-AG6___SPAN__.csv").csv({typed: true});
const d8x = await FileAttachment("../data/__SLUG___products_partners_HS-AG6___SPAN__.csv").csv({typed: true});
const d8m = await FileAttachment("../data/__SLUG___partners_products_HS-AG6___SPAN__.csv").csv({typed: true});
const meta = await FileAttachment("../data/__SLUG___profile___SPAN__.meta.json").json();
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
  rows.map((d) => ({Ano: d.year,
                    [nameLabel]: d.hs6 ? `${d.hs6} — ${trunc(d[nameCol], 40)}` : d[nameCol],
                    Valor: d.value,
                    "Quota (%)": d.share_pct, "Pos.": d.rank})),
  {rows: 10, format: {Ano: (v) => String(v), Valor: usdInt,
                      "Quota (%)": (v) => pct(v), "Pos.": (v) => String(v)}});
```

<div class="note" style="font-size: 0.85rem; color: var(--theme-foreground-muted)">
  Dados de ${years[0]} a ${latestYear} · atualizado em ${meta.generated_at.slice(0, 10)} ·
  valores <em>diretos</em> reportados por __NAME__; valores <em>espelho</em> reportados
  pelos parceiros (soma exclui o agregado «Mundo» para evitar dupla contagem).
</div>

```js
const basis = view(Inputs.radio(
  new Map([
    ["Reportado por __NAME__ (direto)", "direct"],
    ["Reportado pelos parceiros (espelho)", "mirror"]
  ]),
  {label: L.base, value: "direct"}
));
const year = view(Inputs.range([__START__, __END__], {step: 1, value: __END__, label: L.ano}));
```

## ${latestYear} em síntese (base direta)

```js
display(kpiCards(html, [
  {label: "Volume de trocas", value: formatUSD(at(latest, "trade_volume")),
   sub: `__NAME__ ↔ mundo, ${latestYear}`},
  {label: "Exportações", value: formatUSD(at(latest, "exports")), sub: "__NAME__ → mundo"},
  {label: "Importações", value: formatUSD(at(latest, "imports")), sub: "mundo → __NAME__"},
  {label: "Saldo comercial", value: formatUSD(at(latest, "balance")), sub: "perspetiva de __NAME__"}
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

## 2. Exportações de __NAME__

### 2.1 Principais clientes — top 10 em ${year}

```js
const partX = topPartX.filter((d) => d.year === year && d.basis === basis);
display(orEmpty(partX, rankBarChart(Plot, d3, partX, "partner", {usdAxis, formatUSD, pct})));
```

```js
display(orEmpty(partX, rankTable(partX, "partner", "Parceiro")));
```

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
  cada ano, base ${basis === "direct" ? "direta" : "espelho"}).
</div>

__COMP_X__

## 3. Importações de __NAME__

### 3.1 Principais fornecedores — top 10 em ${year}

```js
const partM = topPartM.filter((d) => d.year === year && d.basis === basis);
display(orEmpty(partM, rankBarChart(Plot, d3, partM, "partner", {usdAxis, formatUSD, pct})));
```

```js
display(orEmpty(partM, rankTable(partM, "partner", "Parceiro")));
```

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
  ${L.fonte} · base: ${basis === "direct" ? "valores reportados por __NAME__" : "valores reportados pelos parceiros (espelho)"} ·
  top 10 por ano; produto × parceiro limitado aos 15 principais produtos do período
  (8 parceiros por produto/ano).
</div>

__COMP_M__

## Descarregar

```js
display(html`<p>
  <a href="${FileAttachment("../data/__SLUG___trade_balance___SPAN__.csv").href}" download>Balança comercial (CSV)</a> ·
  <a href="${FileAttachment("../data/__SLUG___top_partners_exports___SPAN__.csv").href}" download>Clientes (CSV)</a> ·
  <a href="${FileAttachment("../data/__SLUG___top_partners_imports___SPAN__.csv").href}" download>Fornecedores (CSV)</a> ·
  <a href="${FileAttachment("../data/__SLUG___top_products_exports_HS-AG6___SPAN__.csv").href}" download>Produtos exportados (CSV)</a> ·
  <a href="${FileAttachment("../data/__SLUG___top_products_imports_HS-AG6___SPAN__.csv").href}" download>Produtos importados (CSV)</a> ·
  <a href="${FileAttachment("../data/__SLUG___products_partners_HS-AG6___SPAN__.csv").href}" download>Produto × parceiro (CSV)</a> ·
  <a href="${FileAttachment("../data/__SLUG___partners_products_HS-AG6___SPAN__.csv").href}" download>Parceiro × produto (CSV)</a> ·
__COMP_DOWNLOADS__  <a href="${FileAttachment("../data/__SLUG___profile___SPAN__.meta.json").href}" download>${L.downloadMeta}</a>
</p>`);
```

---

Dados de origem: bloco de notas `country_trade_profile.ipynb` do projeto
[cipf-comtrade](https://github.com/joaquimrcarvalho/cipf-comtrade) (numeração das
secções 1–3 paralela à do bloco de notas). Metodologia completa em
[Metodologia e fontes](/metodologia) · outros países em [Perfis por país](/perfis).
"""

DATA_DIR = REPO_ROOT / "site" / "src" / "data"


def competition_block(slug: str, name: str, side: str) -> str:
    """Markdown for the §2.4/§3.4 competition explorer (D9/D10; notebook §2.5/§3.5).

    Emitted only when the dataset exists on disk — FileAttachment paths are
    statically checked at build time, so referencing a missing CSV would break
    the build. `side` is "exports" (country's rank among the customer's
    suppliers) or "imports" (rank among the supplier's clients).
    """
    path = DATA_DIR / f"{slug}_competition_{side}_HS-AG6_{SPAN}.csv"
    if not path.exists() or path.stat().st_size < 200:
        return ""  # missing or header-only (no reported data)
    s = "X" if side == "exports" else "M"
    if side == "exports":
        heading = "### 2.4 Concorrência nos mercados dos clientes"
        partner_label, table_head = "Cliente", "Fornecedor"
        intro = (f"Para os principais clientes de {name} e os principais produtos "
                 f"exportados: a quota de {name} e dos outros principais fornecedores "
                 f"nas importações de cada cliente — a posição de {name} entre os "
                 f"fornecedores do cliente (bloco de notas §2.5; base direta).")
        note = (f"Cobertura: 5 principais clientes × 8 principais produtos "
                f"exportados; até 5 concorrentes por mercado, além de {name}.")
    else:
        heading = "### 3.4 Outros clientes dos fornecedores"
        partner_label, table_head = "Fornecedor", "Cliente"
        intro = (f"Para os principais fornecedores de {name} e os principais produtos "
                 f"importados: a quota de {name} e dos outros principais clientes "
                 f"nas exportações de cada fornecedor — a posição de {name} entre os "
                 f"clientes do fornecedor (bloco de notas §3.5; base direta).")
        note = (f"Cobertura: 5 principais fornecedores × 8 principais produtos "
                f"importados; até 5 outros clientes por mercado, além de {name}.")
    return f"""
{heading}

{intro}

```js
const comp{s} = await FileAttachment("../data/{path.name}").csv({{typed: true}});
```

```js
const compPartnerOptions{s} = new Map(
  d3.rollups(comp{s}.filter((d) => d.is_country), (v) => d3.sum(v, (d) => d.value), (d) => d.partner)
    .sort((a, b) => d3.descending(a[1], b[1]))
    .map(([k]) => [k, k])
);
const compPartner{s} = view(Inputs.select(compPartnerOptions{s}, {{label: "{partner_label}"}}));
```

```js
const compProdOptions{s} = new Map(
  d3.rollups(comp{s}.filter((d) => d.partner === compPartner{s}), (v) => d3.sum(v, (d) => d.value), (d) => d.hs6)
    .sort((a, b) => d3.descending(a[1], b[1]))
    .map(([hs6]) => {{
      const desc = comp{s}.find((d) => d.hs6 === hs6)?.description_pt ?? hs6;
      return [`${{hs6}} — ${{trunc(desc, 38)}}`, hs6];
    }})
);
const compProd{s} = view(Inputs.select(compProdOptions{s}, {{label: "Produto (HS6)"}}));
```

```js
const compSel{s} = comp{s}.filter((d) => d.partner === compPartner{s} && d.hs6 === compProd{s});
display(orEmpty(compSel{s}, competitionChart(Plot, d3, compSel{s}, {{pct}})));
```

```js
const compLatest{s} = compSel{s}.length ? Math.max(...compSel{s}.map((d) => d.year)) : null;
display(orEmpty(compSel{s}, Inputs.table(
  compSel{s}.filter((d) => d.year === compLatest{s})
    .map((d) => ({{"Pos.": d.rank, "{table_head}": d.competitor, "Quota (%)": d.share_pct, Valor: d.value}})),
  {{rows: 8, format: {{"Pos.": (v) => String(v), "Quota (%)": (v) => pct(v), Valor: usdInt}}}})));
```

<div style="font-size: 0.85rem; color: var(--theme-foreground-muted)">
  Linha de {name} realçada; a tabela mostra a posição no último ano com dados deste
  mercado. {note}
</div>
"""


def competition_downloads(slug: str) -> str:
    """Extra download links for the Descarregar block, only for existing D9/D10."""
    links = ""
    for side, label in (("exports", "Concorrência nos clientes (CSV)"),
                        ("imports", "Concorrência pelos fornecedores (CSV)")):
        path = DATA_DIR / f"{slug}_competition_{side}_HS-AG6_{SPAN}.csv"
        if path.exists():
            links += ('  <a href="${FileAttachment("../data/' + path.name
                      + '").href}" download>' + label + '</a> ·\n')
    return links


def main():
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    for slug, name in COUNTRIES.items():
        page = (TEMPLATE
                .replace("__COMP_X__", competition_block(slug, name, "exports"))
                .replace("__COMP_M__", competition_block(slug, name, "imports"))
                .replace("__COMP_DOWNLOADS__", competition_downloads(slug))
                .replace("__SLUG__", slug)
                .replace("__NAME__", name)
                .replace("__SPAN__", SPAN)
                .replace("__START__", str(START))
                .replace("__END__", str(END)))
        path = PAGES_DIR / f"{slug}.md"
        path.write_text(page)
        print(f"wrote {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
