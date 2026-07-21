#!/usr/bin/env python3
"""Generate /dados — the open-data download hub for the site.

Scans the committed snapshots in site/src/data/ (plus the .meta.json sidecars
for row counts) and emits site/src/dados.md with literal FileAttachment links
(the Framework resolves those into downloadable asset URLs at build time).

Regenerate whenever the data is re-exported:

    venv/bin/python site/scripts/gen_dados_page.py
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "site" / "src" / "data"
PAGE = REPO_ROOT / "site" / "src" / "dados.md"

SPAN = "2003-2024"

FLOWS = [
    ("cn", "China ↔ PLP", "/china-plp"),
    ("mo", "Macau (RAEM) ↔ PLP", "/macau"),
    ("hk", "Hong Kong (RAEHK) ↔ PLP", "/hong-kong"),
]

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

# profile meta file-key -> Portuguese label (order = presentation order)
PROFILE_DATASETS = [
    ("trade_balance", "Balança comercial"),
    ("top_partners_exports", "Principais clientes"),
    ("top_partners_imports", "Principais fornecedores"),
    ("top_products_exports_HS-AG6", "Produtos exportados (HS-AG6)"),
    ("top_products_imports_HS-AG6", "Produtos importados (HS-AG6)"),
    ("products_partners_HS-AG6", "Produto × parceiro — exportações"),
    ("partners_products_HS-AG6", "Parceiro × produto — importações"),
    ("competition_exports_HS-AG6", "Concorrência nos mercados dos clientes"),
    ("competition_imports_HS-AG6", "Outros clientes dos fornecedores"),
]

HEADER = """# Dados abertos

Todos os conjuntos de dados publicados neste observatório, em CSV (UTF-8) e JSON —
exatamente os ficheiros que alimentam os gráficos. Valores em **USD correntes**;
cobertura 2003–2024. A proveniência, as convenções (base direta vs. espelho) e as
regras de agregação estão em [Metodologia e fontes](/metodologia); cada página de
análise tem também um bloco «Descarregar» com os seus dados.

Citação sugerida e licença de uso: ver [Metodologia e fontes — Como citar](/metodologia#como-citar).
Fonte primária: [UN Comtrade](https://comtradeplus.un.org).

"""

FOOTER = """
---

Gerado por `site/scripts/gen_dados_page.py` a partir dos ficheiros commitados em
`site/src/data/`; regenerar após cada reextração.
"""


def link(fname: str, label: str) -> str:
    """Literal FileAttachment download link for an html`` JS block."""
    return (f'<a href="${{FileAttachment("data/{fname}").href}}" download>'
            f'{label}</a>')


def fmt_rows(n) -> str:
    if n is None:
        return ""
    if n == 0:
        return " — 0 linhas (sem dados)"
    return f" — {n:,} linhas".replace(",", " ")


def flows_section() -> str:
    rows = []
    for cc, name, page in FLOWS:
        csv = f"{cc}_plp_flows_{SPAN}.csv"
        meta_f = DATA_DIR / f"{cc}_plp_flows_{SPAN}.meta.json"
        n = json.loads(meta_f.read_text())["rows"] if meta_f.exists() else None
        rows.append(
            f'      <tr><td><a href=".{page}">{name}</a></td>'
            f'<td>{link(csv, "CSV")}{fmt_rows(n)} · {link(meta_f.name, "meta.json")}</td></tr>')
    body = "\n".join(rows)
    return f"""## Fluxos agregados

Exportações, importações, volume de trocas e saldo com os 9 PLP, por ano e base
(direta/espelho) — as séries das páginas de fluxos.

```js
display(html`
  <table>
    <thead><tr><th>Conjunto</th><th>Ficheiros</th></tr></thead>
    <tbody>
{body}
    </tbody>
  </table>`);
```

"""


def reference_section() -> str:
    plp = DATA_DIR / "plp_countries.json"
    hs = DATA_DIR / "hs_ag6_labels.json"
    n_plp = len(json.loads(plp.read_text())) if plp.exists() else None
    n_hs = len(json.loads(hs.read_text())) if hs.exists() else None
    return f"""## Referência

```js
display(html`<ul>
  <li>{link("plp_countries.json", "plp_countries.json")}{fmt_rows(n_plp).replace("linhas", "países")} — códigos M49 e nomes PT/EN dos PLP.</li>
  <li>{link("hs_ag6_labels.json", "hs_ag6_labels.json")}{fmt_rows(n_hs).replace("linhas", "códigos")} — rótulos EN/PT de todos os códigos HS6 usados nos conjuntos de produtos.</li>
</ul>`);
```

"""


def country_section(slug: str, name: str) -> str:
    meta_f = DATA_DIR / f"{slug}_profile_{SPAN}.meta.json"
    if not meta_f.exists():
        return ""
    meta = json.loads(meta_f.read_text())
    rows = []
    for key, label in PROFILE_DATASETS:
        info = meta["files"].get(key)
        if not info:
            continue
        fname = info["file"]
        if not (DATA_DIR / fname).exists():
            continue
        rows.append(f'      <tr><td>{label}</td>'
                    f'<td>{link(fname, "CSV")}{fmt_rows(info["rows"])}</td></tr>')
    updated = meta["generated_at"][:10]
    body = "\n".join(rows)
    return f"""<details>
  <summary><strong>{name}</strong> — perfil completo (9 conjuntos + meta); extração de {updated} · <a href="./perfis/{slug}">ver perfil</a></summary>

```js
display(html`
  <table>
    <thead><tr><th>Conjunto</th><th>Ficheiro</th></tr></thead>
    <tbody>
{body}
      <tr><td>Metadados</td><td>{link(meta_f.name, "meta.json")}</td></tr>
    </tbody>
  </table>`);
```

</details>

"""


def main() -> None:
    parts = [HEADER, flows_section(), reference_section(),
             "## Perfis por país\n\n",
             "Os 9 conjuntos de cada perfil (D5–D10 na terminologia de "
             "[Metodologia](/metodologia)): balança, principais parceiros e "
             "produtos, detalhe produto × parceiro e análise de concorrência.\n\n"]
    parts += [country_section(slug, name) for slug, name in COUNTRIES.items()]
    parts.append(FOOTER)
    PAGE.write_text("".join(parts))
    print(f"wrote {PAGE.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
