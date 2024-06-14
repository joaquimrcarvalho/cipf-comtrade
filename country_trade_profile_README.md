# Perfil comercial de um país

Perfil comercial de um país. O objetivo é analisar as trocas comerciais de um país com o resto do mundo.

Os dados são gerados pelo bloco de notas [country_trade_profile.ipynb](country_trade_profile.ipynb) que utiliza a base de dados Comtrade da ONU.

Para um país e período de interesse (em um intervalo de anos) ele fornece:

1. Evolução da balança comercial (Importações e Exportações), comparando valor declarado e valor de comércio simétrico
   (e.g. valor de exportações por agregação de importações de outros países, e valor de importações por agregação de exportações de outros países)
   * Exportado para o ficheiro "reports/[PAIS]_trade_balance_2003-2023.xlsx", e gráfico em "reports/<PAÍS>_trade_balance_2003-2023.png" por exº:
   [reports/Angola_trade_balance_2003-2023.xlsx](reports/Angola_trade_balance_2003-2023.xlsx) e [reports/Angola_trade_balance_2003-2023.png](reports/Angola_trade_balance_2003-2023.png)
2. Principais parcerios comerciais (exportações e importações). Inclui:
   1.Exportações: valor das exportações para os países nos cinco (configurável) primeiros parceiros em qualquer um dos anos do período em análise. Por cada país parceiro, é indicado o valor total de exportações no período e a percentagem no total das exportações de cada ano em análise. Os valor das exportações é baseado nas importações reportadas pelos parceiros (é possível
   usar em alternativa os valores reportados de exportação do país em análise).
   1. Com base nestes dados são produzidos os seguintes ficheiros:
      * "reports/[PAIS]_top_export_partners.xlsx": dados retirados da API da UN Comtrade para os anos de 2003 a 2023 uma linha por combinação PAIS-PARCEIRO-ANO.
      * "reports/[PAIS]_top_export_partners_cols.xlsx": quadro simplicado com os anos em linhas e os parceiros em colunas. Por cada parceiro duas colunas: valor de exportações e percentagem no total das exportações do ano.
      * "reports/[PAIS]_export_top_5_partners_2003-2023.xlsx" versão simplificada do ficheiro anterior, apenas com os países que foram um dos cinco principais parceiros em qualquer um dos anos.
      * Um gráfico com a evolução das trocas com os principais países "reports/<PAÍS>_export_partners_2003-2023.png", por exº: [reports/Angola_export_partners_2003-2023.png](reports/Angola_export_partners_2003-2023.png)
3. Principais produtos exportados. Inclui
   1. Produtos: valor das exportações dos produtos nos cinco (configurável) produtos mais exportados em qualquer um dos anos do período em análise. O valor das exportações é baseado nas importações reportadas pelos parceiros (é possível usar em alternativa os valores reportados de exportação do país em análise)。 Os valores reportados são agregados por HS-AG6 (nível
   de detalhe de 6 dígitos, como nas fichas do Banco Mundial, configurável). Depois de agregados, são identificados os cinco produtos mais exportados em qualquer um dos anos do período em análise. Por cada produto, é indicado o valor total de exportações no período e a percentagem no total das exportações de cada ano em análise.
      * "reports/[PAIS]_exports_products_HS-AG6-2003-2023.xlsx"
   2. Principais destinos dos principais produtos. Por cada ano, são identificados os cinco principais destinos dos cinco produtos mais exportados. Para cada produto, é indicado o valor total de exportações das exportações para os cinco (configurável) principais compradores e a percentagem de cada parceiro no total das exportações desse produto desse ano. Estes dados
   permitem analisar a evolução dos destinos dos principais produtos exportados.
      * "reports/[PAIS]_exports_partners_HS-AG6-2003-2023.xlsx"
   3. Fornecedores alternativos para os principais produtos. Por cada país parceiro que importa um dos produtos mais exportados são obtidos
         os fornecedores alternativos do parceiro para esse produto, e calculado o ranking do país em análise dentro do conjunto de fornecedores. Estes dados permitem
         analisar a importância do país em análise como fonte de fornecimento para os parceiros comerciais.
         *"reports/[PAIS]_export_partners_alternative.xlsx"
4. Principais produtos importados. Inclui:
   1. Produtos: valor das importações dos produtos nos cinco (configurável) produtos mais importados no período em análise. O valor das importações é o
         reportado pelo país em análise ou pelas exportações dos parceiros. Os valores reportados são agregados por HS-AG6 (nível de detalhe de 6 dígitos, como nas fichas do Banco Mundial, configurável). Depois de agregados, são identificados os cinco produtos mais importados em qualquer um dos anos do período em análise. Por cada produto, é indicado o valor total de importações no período e a percentagem no total das importações de cada ano em análise.
      * "reports/[PAIS]_imports_products_HS-AG6-2003-2023.xlsx"
