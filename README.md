# cipf-comtrade

Acesso a dados da base `comtrade` da Organização das Nações Unidas
através de `jupyter notebooks`.

Desenvolvido para estimular estudos sobre as relações comerciais
da China com os países de língua portuguesa e o papel da
Região Administrativa Especial de Macau como plataforma de serviços
para essas relações.

## Instalação

Este repositório pode ser clonado para o seu computador com o comando:

```bash
git clone https://github.com/joaquimrcarvalho/cipf-comtrade.git
```

Uma vez clonado deve-se instalar as dependências com o comando:

```bash
pip install -r requirements.txt
```

## Uso

Para usar os notebooks é necessário ter uma chave de acesso à API da
`comtrade` da ONU.

Para aceder à UN Comtrade via API sem limites é necessário uma chave de acesso,
de outro modo os resultados são limitados a 500 linhas.

Para obter a chave de acesso:
* Registo em https://comtradedeveloper.un.org/
* Ir para _Products_
* Selecionar "Premium Individual APIs" (https://comtradedeveloper.un.org/product#product=dataapis)
* Escolher _Subscribe to "comtrade - v1"_
* Esperar pelo email com a chave da API key (demora alguns dias
* Copia a chave para o local indicado no ficheiro `config.ini` antes
  de executar o resto do notebook.

Note que estes notebooks funcionam sem a chave de acesso, mas com limitações
de 500 linhas por pedido, o que pode gerar resultados agregados errados.

## Inicialização

Execute o notebook [0-comtrade-setup-first.ipynb](0-comtrade-setup-first.ipynb) para
configurar a chave de acesso à API da `comtrade` da ONU.

# Lista de notebooks disponíveis

1. [cn_plp_import_export.ipynb](cn_plp_import_export.ipynb) - Análise das importações e exportações da China com os países de língua portuguesa. Fornece valor das importações, exportações, volume de trocas (importaç~oes + exportações) e balança comercial (exportações - importações).
   1. Produz adicionalmente tabelas Excel com os resultados de forma comparável com os dados anualmentecpublicados pelo Fórum Macau.
   2. Produz também gráficos em formato PNG. Ficheiros produzidos são guardados na pasta `reports`.

2. [cn_plp_commodities.ipynb](cn_plp_commodities.ipynb) - Análise da composição das importações e exportações entre a China e os países de língua portuguesa através dos produtos mais trocados.
   1. Por cada PLP analisa ano a ano os cinco (configurável) produtos mais importados e exportados pela China e produz uma tabela Excel.
   2. Gera também um relatório em texto que assinala as principais variações contidas nos dados ano longo do tempo: novos produtos entrados no "top", produtos que saíram, produtos que subiram ou desceram de posição e variação anual do valor de cada tipo de produto.
   3. Produz adicionalmente um quadro detalhado da
composição das categorias de produtos trocados até seis dígitos da classificação HS.

1. [country_trade_profile.ipynb](country_trade_profile.ipynb) - Análise do perfil comercial
de um país. Analise os principais produtos exportados e importados e os principais parceiros comerciais.
   1. Evolução dos principais produtos exportados e importados.
   2. Evolução dos principais parceiros comerciais.
   3. Análise da dependências de produtos e parceiros comerciais, ou seja o peso
      do país em análise nas exportações e importações dos seus parceiros comerciais
      principais.

## Autor

Joaquim Carvalho, Universidade Politécnica de Macau.
