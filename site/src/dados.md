# Dados abertos

Todos os conjuntos de dados publicados neste observatório, em CSV (UTF-8) e JSON —
exatamente os ficheiros que alimentam os gráficos. Valores em **USD correntes**;
cobertura 2003–2024. A proveniência, as convenções (base direta vs. espelho) e as
regras de agregação estão em [Metodologia e fontes](/metodologia); cada página de
análise tem também um bloco «Descarregar» com os seus dados.

Citação sugerida e licença de uso: ver [Metodologia e fontes — Como citar](/metodologia#como-citar).
Fonte primária: [UN Comtrade](https://comtradeplus.un.org).

## Fluxos agregados

Exportações, importações, volume de trocas e saldo com os 9 PLP, por ano e base
(direta/espelho) — as séries das páginas de fluxos.

```js
display(html`
  <table>
    <thead><tr><th>Conjunto</th><th>Ficheiros</th></tr></thead>
    <tbody>
      <tr><td><a href="./china-plp">China ↔ PLP</a></td><td><a href="${FileAttachment("data/cn_plp_flows_2003-2024.csv").href}" download>CSV</a> — 346 linhas · <a href="${FileAttachment("data/cn_plp_flows_2003-2024.meta.json").href}" download>meta.json</a></td></tr>
      <tr><td><a href="./macau">Macau (RAEM) ↔ PLP</a></td><td><a href="${FileAttachment("data/mo_plp_flows_2003-2024.csv").href}" download>CSV</a> — 201 linhas · <a href="${FileAttachment("data/mo_plp_flows_2003-2024.meta.json").href}" download>meta.json</a></td></tr>
      <tr><td><a href="./hong-kong">Hong Kong (RAEHK) ↔ PLP</a></td><td><a href="${FileAttachment("data/hk_plp_flows_2003-2024.csv").href}" download>CSV</a> — 319 linhas · <a href="${FileAttachment("data/hk_plp_flows_2003-2024.meta.json").href}" download>meta.json</a></td></tr>
    </tbody>
  </table>`);
```

## Referência

```js
display(html`<ul>
  <li><a href="${FileAttachment("data/plp_countries.json").href}" download>plp_countries.json</a> — 9 países — códigos M49 e nomes PT/EN dos PLP.</li>
  <li><a href="${FileAttachment("data/hs_ag6_labels.json").href}" download>hs_ag6_labels.json</a> — 513 códigos — rótulos EN/PT de todos os códigos HS6 usados nos conjuntos de produtos.</li>
</ul>`);
```

## Perfis por país

Os 9 conjuntos de cada perfil: balança, principais parceiros e produtos, detalhe produto × parceiro e análise de concorrência.

<details>
  <summary><strong>Angola</strong> — perfil completo (9 conjuntos + meta); extração de 2026-07-21 · <a href="./perfis/angola">ver perfil</a></summary>

```js
display(html`
  <table>
    <thead><tr><th>Conjunto</th><th>Ficheiro</th></tr></thead>
    <tbody>
      <tr><td>Balança comercial</td><td><a href="${FileAttachment("data/angola_trade_balance_2003-2024.csv").href}" download>CSV</a> — 44 linhas</td></tr>
      <tr><td>Principais clientes</td><td><a href="${FileAttachment("data/angola_top_partners_exports_2003-2024.csv").href}" download>CSV</a> — 430 linhas</td></tr>
      <tr><td>Principais fornecedores</td><td><a href="${FileAttachment("data/angola_top_partners_imports_2003-2024.csv").href}" download>CSV</a> — 430 linhas</td></tr>
      <tr><td>Produtos exportados (HS-AG6)</td><td><a href="${FileAttachment("data/angola_top_products_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 405 linhas</td></tr>
      <tr><td>Produtos importados (HS-AG6)</td><td><a href="${FileAttachment("data/angola_top_products_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 430 linhas</td></tr>
      <tr><td>Produto × parceiro — exportações</td><td><a href="${FileAttachment("data/angola_products_partners_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 3 427 linhas</td></tr>
      <tr><td>Parceiro × produto — importações</td><td><a href="${FileAttachment("data/angola_partners_products_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 8 003 linhas</td></tr>
      <tr><td>Concorrência nos mercados dos clientes</td><td><a href="${FileAttachment("data/angola_competition_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 3 927 linhas</td></tr>
      <tr><td>Outros clientes dos fornecedores</td><td><a href="${FileAttachment("data/angola_competition_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 4 175 linhas</td></tr>
      <tr><td>Metadados</td><td><a href="${FileAttachment("data/angola_profile_2003-2024.meta.json").href}" download>meta.json</a></td></tr>
    </tbody>
  </table>`);
```

</details>

<details>
  <summary><strong>Brasil</strong> — perfil completo (9 conjuntos + meta); extração de 2026-07-21 · <a href="./perfis/brasil">ver perfil</a></summary>

```js
display(html`
  <table>
    <thead><tr><th>Conjunto</th><th>Ficheiro</th></tr></thead>
    <tbody>
      <tr><td>Balança comercial</td><td><a href="${FileAttachment("data/brasil_trade_balance_2003-2024.csv").href}" download>CSV</a> — 44 linhas</td></tr>
      <tr><td>Principais clientes</td><td><a href="${FileAttachment("data/brasil_top_partners_exports_2003-2024.csv").href}" download>CSV</a> — 440 linhas</td></tr>
      <tr><td>Principais fornecedores</td><td><a href="${FileAttachment("data/brasil_top_partners_imports_2003-2024.csv").href}" download>CSV</a> — 440 linhas</td></tr>
      <tr><td>Produtos exportados (HS-AG6)</td><td><a href="${FileAttachment("data/brasil_top_products_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 440 linhas</td></tr>
      <tr><td>Produtos importados (HS-AG6)</td><td><a href="${FileAttachment("data/brasil_top_products_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 440 linhas</td></tr>
      <tr><td>Produto × parceiro — exportações</td><td><a href="${FileAttachment("data/brasil_products_partners_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 8 151 linhas</td></tr>
      <tr><td>Parceiro × produto — importações</td><td><a href="${FileAttachment("data/brasil_partners_products_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 7 103 linhas</td></tr>
      <tr><td>Concorrência nos mercados dos clientes</td><td><a href="${FileAttachment("data/brasil_competition_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 3 978 linhas</td></tr>
      <tr><td>Outros clientes dos fornecedores</td><td><a href="${FileAttachment("data/brasil_competition_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 3 898 linhas</td></tr>
      <tr><td>Metadados</td><td><a href="${FileAttachment("data/brasil_profile_2003-2024.meta.json").href}" download>meta.json</a></td></tr>
    </tbody>
  </table>`);
```

</details>

<details>
  <summary><strong>Cabo Verde</strong> — perfil completo (9 conjuntos + meta); extração de 2026-07-21 · <a href="./perfis/cabo-verde">ver perfil</a></summary>

```js
display(html`
  <table>
    <thead><tr><th>Conjunto</th><th>Ficheiro</th></tr></thead>
    <tbody>
      <tr><td>Balança comercial</td><td><a href="${FileAttachment("data/cabo-verde_trade_balance_2003-2024.csv").href}" download>CSV</a> — 44 linhas</td></tr>
      <tr><td>Principais clientes</td><td><a href="${FileAttachment("data/cabo-verde_top_partners_exports_2003-2024.csv").href}" download>CSV</a> — 426 linhas</td></tr>
      <tr><td>Principais fornecedores</td><td><a href="${FileAttachment("data/cabo-verde_top_partners_imports_2003-2024.csv").href}" download>CSV</a> — 440 linhas</td></tr>
      <tr><td>Produtos exportados (HS-AG6)</td><td><a href="${FileAttachment("data/cabo-verde_top_products_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 427 linhas</td></tr>
      <tr><td>Produtos importados (HS-AG6)</td><td><a href="${FileAttachment("data/cabo-verde_top_products_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 440 linhas</td></tr>
      <tr><td>Produto × parceiro — exportações</td><td><a href="${FileAttachment("data/cabo-verde_products_partners_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 1 944 linhas</td></tr>
      <tr><td>Parceiro × produto — importações</td><td><a href="${FileAttachment("data/cabo-verde_partners_products_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 6 353 linhas</td></tr>
      <tr><td>Concorrência nos mercados dos clientes</td><td><a href="${FileAttachment("data/cabo-verde_competition_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 3 051 linhas</td></tr>
      <tr><td>Outros clientes dos fornecedores</td><td><a href="${FileAttachment("data/cabo-verde_competition_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 4 677 linhas</td></tr>
      <tr><td>Metadados</td><td><a href="${FileAttachment("data/cabo-verde_profile_2003-2024.meta.json").href}" download>meta.json</a></td></tr>
    </tbody>
  </table>`);
```

</details>

<details>
  <summary><strong>Guiné-Bissau</strong> — perfil completo (9 conjuntos + meta); extração de 2026-07-21 · <a href="./perfis/guine-bissau">ver perfil</a></summary>

```js
display(html`
  <table>
    <thead><tr><th>Conjunto</th><th>Ficheiro</th></tr></thead>
    <tbody>
      <tr><td>Balança comercial</td><td><a href="${FileAttachment("data/guine-bissau_trade_balance_2003-2024.csv").href}" download>CSV</a> — 44 linhas</td></tr>
      <tr><td>Principais clientes</td><td><a href="${FileAttachment("data/guine-bissau_top_partners_exports_2003-2024.csv").href}" download>CSV</a> — 290 linhas</td></tr>
      <tr><td>Principais fornecedores</td><td><a href="${FileAttachment("data/guine-bissau_top_partners_imports_2003-2024.csv").href}" download>CSV</a> — 300 linhas</td></tr>
      <tr><td>Produtos exportados (HS-AG6)</td><td><a href="${FileAttachment("data/guine-bissau_top_products_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 269 linhas</td></tr>
      <tr><td>Produtos importados (HS-AG6)</td><td><a href="${FileAttachment("data/guine-bissau_top_products_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 300 linhas</td></tr>
      <tr><td>Produto × parceiro — exportações</td><td><a href="${FileAttachment("data/guine-bissau_products_partners_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 795 linhas</td></tr>
      <tr><td>Parceiro × produto — importações</td><td><a href="${FileAttachment("data/guine-bissau_partners_products_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 3 455 linhas</td></tr>
      <tr><td>Concorrência nos mercados dos clientes</td><td><a href="${FileAttachment("data/guine-bissau_competition_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 3 642 linhas</td></tr>
      <tr><td>Outros clientes dos fornecedores</td><td><a href="${FileAttachment("data/guine-bissau_competition_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 3 652 linhas</td></tr>
      <tr><td>Metadados</td><td><a href="${FileAttachment("data/guine-bissau_profile_2003-2024.meta.json").href}" download>meta.json</a></td></tr>
    </tbody>
  </table>`);
```

</details>

<details>
  <summary><strong>Guiné Equatorial</strong> — perfil completo (9 conjuntos + meta); extração de 2026-07-21 · <a href="./perfis/guine-equatorial">ver perfil</a></summary>

```js
display(html`
  <table>
    <thead><tr><th>Conjunto</th><th>Ficheiro</th></tr></thead>
    <tbody>
      <tr><td>Balança comercial</td><td><a href="${FileAttachment("data/guine-equatorial_trade_balance_2003-2024.csv").href}" download>CSV</a> — 44 linhas</td></tr>
      <tr><td>Principais clientes</td><td><a href="${FileAttachment("data/guine-equatorial_top_partners_exports_2003-2024.csv").href}" download>CSV</a> — 220 linhas</td></tr>
      <tr><td>Principais fornecedores</td><td><a href="${FileAttachment("data/guine-equatorial_top_partners_imports_2003-2024.csv").href}" download>CSV</a> — 220 linhas</td></tr>
      <tr><td>Produtos exportados (HS-AG6)</td><td><a href="${FileAttachment("data/guine-equatorial_top_products_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 220 linhas</td></tr>
      <tr><td>Produtos importados (HS-AG6)</td><td><a href="${FileAttachment("data/guine-equatorial_top_products_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 220 linhas</td></tr>
      <tr><td>Produto × parceiro — exportações</td><td><a href="${FileAttachment("data/guine-equatorial_products_partners_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 1 833 linhas</td></tr>
      <tr><td>Parceiro × produto — importações</td><td><a href="${FileAttachment("data/guine-equatorial_partners_products_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 3 151 linhas</td></tr>
      <tr><td>Concorrência nos mercados dos clientes</td><td><a href="${FileAttachment("data/guine-equatorial_competition_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 0 linhas (sem dados)</td></tr>
      <tr><td>Outros clientes dos fornecedores</td><td><a href="${FileAttachment("data/guine-equatorial_competition_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 0 linhas (sem dados)</td></tr>
      <tr><td>Metadados</td><td><a href="${FileAttachment("data/guine-equatorial_profile_2003-2024.meta.json").href}" download>meta.json</a></td></tr>
    </tbody>
  </table>`);
```

</details>

<details>
  <summary><strong>Moçambique</strong> — perfil completo (9 conjuntos + meta); extração de 2026-07-21 · <a href="./perfis/mocambique">ver perfil</a></summary>

```js
display(html`
  <table>
    <thead><tr><th>Conjunto</th><th>Ficheiro</th></tr></thead>
    <tbody>
      <tr><td>Balança comercial</td><td><a href="${FileAttachment("data/mocambique_trade_balance_2003-2024.csv").href}" download>CSV</a> — 44 linhas</td></tr>
      <tr><td>Principais clientes</td><td><a href="${FileAttachment("data/mocambique_top_partners_exports_2003-2024.csv").href}" download>CSV</a> — 440 linhas</td></tr>
      <tr><td>Principais fornecedores</td><td><a href="${FileAttachment("data/mocambique_top_partners_imports_2003-2024.csv").href}" download>CSV</a> — 440 linhas</td></tr>
      <tr><td>Produtos exportados (HS-AG6)</td><td><a href="${FileAttachment("data/mocambique_top_products_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 440 linhas</td></tr>
      <tr><td>Produtos importados (HS-AG6)</td><td><a href="${FileAttachment("data/mocambique_top_products_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 440 linhas</td></tr>
      <tr><td>Produto × parceiro — exportações</td><td><a href="${FileAttachment("data/mocambique_products_partners_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 4 595 linhas</td></tr>
      <tr><td>Parceiro × produto — importações</td><td><a href="${FileAttachment("data/mocambique_partners_products_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 6 274 linhas</td></tr>
      <tr><td>Concorrência nos mercados dos clientes</td><td><a href="${FileAttachment("data/mocambique_competition_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 2 989 linhas</td></tr>
      <tr><td>Outros clientes dos fornecedores</td><td><a href="${FileAttachment("data/mocambique_competition_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 4 233 linhas</td></tr>
      <tr><td>Metadados</td><td><a href="${FileAttachment("data/mocambique_profile_2003-2024.meta.json").href}" download>meta.json</a></td></tr>
    </tbody>
  </table>`);
```

</details>

<details>
  <summary><strong>Portugal</strong> — perfil completo (9 conjuntos + meta); extração de 2026-07-21 · <a href="./perfis/portugal">ver perfil</a></summary>

```js
display(html`
  <table>
    <thead><tr><th>Conjunto</th><th>Ficheiro</th></tr></thead>
    <tbody>
      <tr><td>Balança comercial</td><td><a href="${FileAttachment("data/portugal_trade_balance_2003-2024.csv").href}" download>CSV</a> — 44 linhas</td></tr>
      <tr><td>Principais clientes</td><td><a href="${FileAttachment("data/portugal_top_partners_exports_2003-2024.csv").href}" download>CSV</a> — 440 linhas</td></tr>
      <tr><td>Principais fornecedores</td><td><a href="${FileAttachment("data/portugal_top_partners_imports_2003-2024.csv").href}" download>CSV</a> — 440 linhas</td></tr>
      <tr><td>Produtos exportados (HS-AG6)</td><td><a href="${FileAttachment("data/portugal_top_products_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 440 linhas</td></tr>
      <tr><td>Produtos importados (HS-AG6)</td><td><a href="${FileAttachment("data/portugal_top_products_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 440 linhas</td></tr>
      <tr><td>Produto × parceiro — exportações</td><td><a href="${FileAttachment("data/portugal_products_partners_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 8 623 linhas</td></tr>
      <tr><td>Parceiro × produto — importações</td><td><a href="${FileAttachment("data/portugal_partners_products_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 7 579 linhas</td></tr>
      <tr><td>Concorrência nos mercados dos clientes</td><td><a href="${FileAttachment("data/portugal_competition_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 4 955 linhas</td></tr>
      <tr><td>Outros clientes dos fornecedores</td><td><a href="${FileAttachment("data/portugal_competition_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 4 878 linhas</td></tr>
      <tr><td>Metadados</td><td><a href="${FileAttachment("data/portugal_profile_2003-2024.meta.json").href}" download>meta.json</a></td></tr>
    </tbody>
  </table>`);
```

</details>

<details>
  <summary><strong>São Tomé e Príncipe</strong> — perfil completo (9 conjuntos + meta); extração de 2026-07-21 · <a href="./perfis/sao-tome-e-principe">ver perfil</a></summary>

```js
display(html`
  <table>
    <thead><tr><th>Conjunto</th><th>Ficheiro</th></tr></thead>
    <tbody>
      <tr><td>Balança comercial</td><td><a href="${FileAttachment("data/sao-tome-e-principe_trade_balance_2003-2024.csv").href}" download>CSV</a> — 44 linhas</td></tr>
      <tr><td>Principais clientes</td><td><a href="${FileAttachment("data/sao-tome-e-principe_top_partners_exports_2003-2024.csv").href}" download>CSV</a> — 430 linhas</td></tr>
      <tr><td>Principais fornecedores</td><td><a href="${FileAttachment("data/sao-tome-e-principe_top_partners_imports_2003-2024.csv").href}" download>CSV</a> — 430 linhas</td></tr>
      <tr><td>Produtos exportados (HS-AG6)</td><td><a href="${FileAttachment("data/sao-tome-e-principe_top_products_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 424 linhas</td></tr>
      <tr><td>Produtos importados (HS-AG6)</td><td><a href="${FileAttachment("data/sao-tome-e-principe_top_products_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 430 linhas</td></tr>
      <tr><td>Produto × parceiro — exportações</td><td><a href="${FileAttachment("data/sao-tome-e-principe_products_partners_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 1 503 linhas</td></tr>
      <tr><td>Parceiro × produto — importações</td><td><a href="${FileAttachment("data/sao-tome-e-principe_partners_products_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 4 560 linhas</td></tr>
      <tr><td>Concorrência nos mercados dos clientes</td><td><a href="${FileAttachment("data/sao-tome-e-principe_competition_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 2 768 linhas</td></tr>
      <tr><td>Outros clientes dos fornecedores</td><td><a href="${FileAttachment("data/sao-tome-e-principe_competition_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 2 991 linhas</td></tr>
      <tr><td>Metadados</td><td><a href="${FileAttachment("data/sao-tome-e-principe_profile_2003-2024.meta.json").href}" download>meta.json</a></td></tr>
    </tbody>
  </table>`);
```

</details>

<details>
  <summary><strong>Timor-Leste</strong> — perfil completo (9 conjuntos + meta); extração de 2026-07-21 · <a href="./perfis/timor-leste">ver perfil</a></summary>

```js
display(html`
  <table>
    <thead><tr><th>Conjunto</th><th>Ficheiro</th></tr></thead>
    <tbody>
      <tr><td>Balança comercial</td><td><a href="${FileAttachment("data/timor-leste_trade_balance_2003-2024.csv").href}" download>CSV</a> — 44 linhas</td></tr>
      <tr><td>Principais clientes</td><td><a href="${FileAttachment("data/timor-leste_top_partners_exports_2003-2024.csv").href}" download>CSV</a> — 320 linhas</td></tr>
      <tr><td>Principais fornecedores</td><td><a href="${FileAttachment("data/timor-leste_top_partners_imports_2003-2024.csv").href}" download>CSV</a> — 320 linhas</td></tr>
      <tr><td>Produtos exportados (HS-AG6)</td><td><a href="${FileAttachment("data/timor-leste_top_products_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 320 linhas</td></tr>
      <tr><td>Produtos importados (HS-AG6)</td><td><a href="${FileAttachment("data/timor-leste_top_products_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 320 linhas</td></tr>
      <tr><td>Produto × parceiro — exportações</td><td><a href="${FileAttachment("data/timor-leste_products_partners_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 1 497 linhas</td></tr>
      <tr><td>Parceiro × produto — importações</td><td><a href="${FileAttachment("data/timor-leste_partners_products_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 3 644 linhas</td></tr>
      <tr><td>Concorrência nos mercados dos clientes</td><td><a href="${FileAttachment("data/timor-leste_competition_exports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 4 197 linhas</td></tr>
      <tr><td>Outros clientes dos fornecedores</td><td><a href="${FileAttachment("data/timor-leste_competition_imports_HS-AG6_2003-2024.csv").href}" download>CSV</a> — 3 385 linhas</td></tr>
      <tr><td>Metadados</td><td><a href="${FileAttachment("data/timor-leste_profile_2003-2024.meta.json").href}" download>meta.json</a></td></tr>
    </tbody>
  </table>`);
```

</details>


---

Gerado por `site/scripts/gen_dados_page.py` a partir dos ficheiros commitados em
`site/src/data/`; regenerar após cada reextração.
