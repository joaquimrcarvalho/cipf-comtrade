# Perfil comercial de um país

Perfil comercial de um país. O objetivo é analisar as trocas comerciais de um país com o resto do mundo.

Os dados são gerados pelo bloco de notas [country_trade_profile.ipynb](country_trade_profile.ipynb) que utiliza a base de dados Comtrade da ONU.

Para um país e período de interesse (em um intervalo de anos) ele fornece:

## 1. Balança comercial
### 1.1. Evolução da balança comercial (Importações e Exportações)

Compara o valor declarado e valor de comércio simétrico
(e.g. valor de exportações por agregação de importações de outros países, e valor de importações por agregação de exportações de outros países)

#### Ficheiros
* Excel: "reports/[PAIS]_1.1_trade_balance_2003-2023.xlsx" por exº:
[Angola_1.1_trade_balance_2003-2023.xlsx](reports/Angola_1.1_trade_balance_2003-2023.xlsx)
* Gráfico: "<PAÍS>_1.2_trade_balance_2003-2023.png", por exº:
   [reports/Angola_1.2_trade_balance_2003-2023.png](reports/Angola_1.2_trade_balance_2003-2023.png)

## 2. Exportações

### 2.1 Principais destinos das exportações (clientes)

Calcula o valor das exportações para os países nos cinco (configurável)
primeiros parceiros em qualquer um dos anos do período em análise. Por cada país
parceiro, é recolhido o valor total de exportações no período e a percentagem no
total das exportações de cada ano em análise.

> Quem são os principais clientes de Angola?

O valor das exportações é baseado
nas importações reportadas pelos parceiros (é possível usar em alternativa os
valores reportados de exportação do país em análise).

O bloco de notas pode fazer opcionalmente uma análise de simetria, comparando os
valores de exportação com os valores de importação reportados pelos parceiros, para
um determinado parceiro/ano.

Com base nestes dados são produzidos os seguintes ficheiros:

#### Ficheiros

 * "reports/[PAIS]_2.1.1_top_export_partners.xlsx": dados retirados da API da UN Comtrade para os anos de 2003 a 2023 uma linha por combinação PAIS-PARCEIRO-ANO.
 * "reports/[PAIS]_2.1.2_top_export_partners_cols.xlsx": quadro invertido com os anos em linhas e os parceiros em colunas. Por cada parceiro duas colunas: valor de exportações e percentagem no total das exportações do ano.
 * "reports/[PAIS]_2.1.3_export_top_5_partners_2003-2023.xlsx" versão simplificada do ficheiro anterior, apenas com os países que foram um dos cinco principais parceiros em qualquer um dos anos.
 * Um gráfico com a evolução das exportações com os principais países "reports/<PAÍS>_2.1.4_export_partners_2003-2023.png", por exº: [reports/Angola_2.1.4_export_partners_2003-2023.png](reports/Angola_2.1.4_export_partners_2003-2023.png)
 * Opcionalmente um gráfico que compara num determinado ano as exportações declaradas pelo país em análise
    com as importações reportadas pelo parceiro "reports/<PAÍS>_2.1.4_export_import_symmetry_2008.xlsx", por exº: [reports/Mozambique_2.1.4_export_import_symmetry_2008.xlsx](Mozambique_2.1.4_export_import_symmetry_2008.xlsx)

### 2.2 Principais produtos exportados

Valor das exportações dos produtos nos cinco (configurável) produtos
mais exportados em qualquer um dos anos do período em análise.

> Quais as principais exportações de Angola?

O valor das exportações é baseado nas importações reportadas
pelos parceiros (é possível usar em alternativa os valores reportados
de exportação do país em análise)。

Os valores reportados são agregados por HS-AG6 (nível
de detalhe de 6 dígitos, como nas fichas do Banco Mundial, configurável).
Comparar com Banco Mundial, WITS, p. exº: [https://wits.worldbank.org/countrysnapshot/en/AGO](https://wits.worldbank.org/countrysnapshot/en/AGO)

Depois de agregados, são identificados os cinco produtos mais exportados em
qualquer um dos anos do período em análise.

Por cada produto, é indicado o valor total de
exportações no período e a percentagem no total das exportações de cada ano em
análise.

#### Ficheiros

* "reports/[PAIS]_2.2_exports_products_HS-AG6-2003-2023.xlsx", p. exº: [reports/Angola_2.2_exports_products_HS-AG6-2003-2023.xlsx](reports/Angola_2.2_exports_products_HS-AG6-2003-2023.xlsx)

### 2.3 Principais produtos exportados e principais clientes

Principais *destinos/clients* dos principais *produtos*.

> Quem compra o petróleo de Angola?

Por cada ano, são identificados os cinco principais destinos dos produtos mais exportados. Para cada produto, é indicado o valor total de exportações para os cinco (configurável) principais compradores e a percentagem de cada parceiro no total das exportações desse produto desse ano. O valor das exportações é estimado a partir das
importações dos países parceiros do país em análise.

Estes dados permitem analisar a evolução
dos destinos dos principais produtos exportados.

#### Ficheiros

* [PAIS]_2.3_exports_products_partners_HS-AG6-2003-2023.xlsx

### 2.4 Principais clientes de exportações e principais produtos exportados

Principais *produtos* vendidos aos principais clientes.

Por cada ano são identificados os cinco principais clientes das exportações
do país em análise e contabilizados os cinco principais produtos comprados
por esses clientes.

Estes dados permitem analisar a composição das exportações para os maiores
clientes e a respectiva diversificação ou concentração

> O que compra a China a Angola (além de petróleo)?

#### Ficheiros
* [PAÍS]_2.4_exports_partners_products_HS-AG6-2003-2023.xlsx

### 2.5 Fornecedores alternativos dos produtos exportados

Por cada país parceiro que importa um dos produtos mais exportados são obtidos
os fornecedores alternativos do parceiro para esse produto, e calculado o ranking do país em análise dentro do conjunto de fornecedores.

Estes dados permitem analisar a importância do país em análise como fonte de
fornecimento para os parceiros comerciais.ranking do país de interesse nos fornecedores do produto a cada cliente.

> Além de Angola quem mais fornece petróleo à China e qual o ranking de Angola entre os fornecedores?

#### Ficheiros
* [PAÍS]_2.5.1_export_partners_alternative.xlsx todos os fornecedores alternativos
  de todos os produtos principais exportados pelo país de interesse.
* [PAÍS]_2.5.2_export_partners_alternative_relevant.xlsx subconjunto da listagem
  anterior só com as linhas respeitantes ao país em análise quando o ranking entre
  os fornecedores é igual ou inferior a 25 (configurável).



## 3. Importações


### 3.1 Principais origens das importações (fornecedores)

Por cada ano são identificados os principais países que forneceram os principais produtos
importados durante o período em análise. Permite analisar a evolução no tempo dos principais
fornecedores do país.

#### Ficheiros

* "[PAIS]_3.1.1_top_import_partners.xlsx": dados retirados da API da UN Comtrade, uma linha por combinação PAIS-PARCEIRO-ANO.
* "[PAIS]_3.1.2_top_import_partners_cols.xlsx": quadro simplicado com os anos em linhas e os parceiros em colunas. Por cada parceiro duas colunas: valor de importaçoes e percentagem no total das importações do ano.
* "[PAIS]_3.1.3_import_top_5_partners_2003-2023" versão simplificada do ficheiro anterior, apenas com os países que foram um dos cinco principais parceiros em qualquer um dos anos.
* Um gráfico com a evolução das importações dos principais países fornecedores "[PAÍS]_3.1.4_import_partners_2003-2023.png", por exº: [reports/Angola_3.1.4_import_partners_2003-2023.png](reports/Angola_3.1.4_import_partners_2003-2023.png)

### 3.2 Principais produtos importados

 *Produtos*: valor das importações dos produtos nos cinco (configurável)
produtos mais importados no período em análise.

> Quais os principais produtos importados por Angola?

O valor das importações é o reportado pelo país em análise ou pelas exportações dos parceiros.

Os valores reportados são agregados por HS-AG6 (nível de detalhe de 6 dígitos, como nas fichas
do Banco Mundial, configurável). Depois de agregados, são identificados os cinco produtos mais
importados em qualquer um dos anos do período em análise. Por cada produto, é indicado o valor
total de importações no período e a percentagem no total das importações de cada ano em análise.

Note[^1]

#### Ficheiros

      * "reports/[PAIS]_3.2_imports_products_HS-AG6-2003-2023.xlsx" (nem todos os países
         disponibilizam dados para todos os anos)



   1. *Fornecedores*:
      * "reports/[PAIS]_imports_products_partners_HS-AG6-2007-2022.xlsx


### 3.3 Principais produtos importados e principais fornecedores

Para os principais produtos importados em cada ano, calcular quais os
principais fornecedores de cada produto.

> Quais os principais fornecedores de equipamento de prospeção petrolífera
a Angola?

#### Ficheiros

* [PAÍS]_3.3_imports_products_partners_HS-AG6-2007-2022.xlsx


### 3.4 Principais fornecedores e produtos fornecidos

Para os principais fornecedores calcula o valor em cada ano dos
principais produtos fornecidos.

> O que Angola compra a Portugal?

#### Ficheiros

* [PAÍS]_3.4_imports_partners_products_HS-AG6-2007-2022.xlsx


### 3.5 Clientes alternativos dos principais fornecedores

Para os principais fornecedores do país em análise analisar, para
os produtos fornecidos, quais os outros clientes dos fornecedores e
calcular a posição relativa do país em análise entre os clientes
dos fornedores principais.

Estes dados permitem analisar até que ponto os fornecedores
estão dependentes de Angola como cliente.

> A quem mais os USA vendem equipamente de prospecção petrolífera e
qual a posição de Angola entre os clientes?

#### Ficheiros
* [PAÍS]_3.5.1_import_partners_alternative.xlsx todos os clientes alternativos dos fornecedores das principais importações do país em análise.
* [PAÍS]_3.5.2_import_partners_alternative_relevant.xlsx subconjunto da listagem
  anterior só com as linhas respeitantes ao país em análise quando o ranking entre
  os clientes é igual ou inferior a 25 (configurável).

## Validation

Compare results with:

* [https://wits.worldbank.org/countrysnapshot/en/AGO](https://wits.worldbank.org/countrysnapshot/en/AGO)
  *

## Notes

[^1]: For Angola results match https://trendeconomy.com/data/h2/Angola/TOTAL for AG2 and AG4 but not https://www.statista.com/statistics/1143152/value-of-imports-into-angola-by-category/  and close but not same as https://globaledge.msu.edu/countries/angola/tradestats . The imports match World Bank Wits data mostly, but in some years there seems to be a mismatch of HS Codes, with different descriptions in Wits
and values that sometimes match AG4 and not AG6 (2015,total is AG4:2710 not AG6:271012 )
and in same cases match the first 5 digits (2015: 73042 "Casings tubing...", 2021 10011, Durum Wheat) TODO: link to world bank wits data
