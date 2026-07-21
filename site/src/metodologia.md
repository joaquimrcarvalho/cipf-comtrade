# Metodologia e fontes

Documentação dos dados, convenções e validação deste observatório. O objetivo é que
cada número apresentado no site seja reproduzível a partir da fonte primária.

## Fonte

- **UN Comtrade** ([comtradeplus.un.org](https://comtradeplus.un.org)) — estatísticas
  oficiais de comércio de mercadorias reportadas pelos países às Nações Unidas.
  Usamos os dados *finais* (não *preliminares*), periodicidade **anual**,
  classificação de produtos **HS** (*Harmonized System*), valores em **USD correntes**.
- O acesso é feito pela API oficial através do módulo aberto
  [`comtradetools.py`](https://github.com/joaquimrcarvalho/cipf-comtrade/blob/main/comtradetools.py)
  do projeto, que trata da divisão de pedidos em blocos de 12 períodos, da cache
  local (validade de 90 dias) e dos limites de taxa da API.
- A extração para o site é feita por *scripts* dedicados
  (`site/scripts/export_site_data.py` e `site/scripts/export_profiles.py`), cujos
  resultados — ficheiros CSV/JSON — ficam registados no repositório com a respetiva
  data de geração (`generated_at` em cada ficheiro `.meta.json`).

## Base direta vs. base espelho

Para cada fluxo comercial existem duas fontes possíveis:

- **base direta** — valores reportados pelo próprio país (ex.: exportações de Angola
  reportadas por Angola);
- **base espelho** (simétrica) — os mesmos fluxos inferidos dos reportes dos
  parceiros (ex.: exportações de Angola inferidas das importações que os parceiros
  declaram de Angola).

As duas bases **divergem legitimamente**: as importações são tipicamente valoradas
CIF (com custo, seguro e frete) e as exportações FOB; há falhas de reporte,
diferenças de classificação e supressões por confidencialidade. O site apresenta
sempre as duas bases, devidamente identificadas, em vez de escolher uma — a
divergência é informativa sobre a qualidade do reporte.

**Regra de agregação do espelho:** os totais espelho somam os reportes individuais
dos parceiros. Verificámos ao vivo (2026-07-19) que as respostas com `reporter=all`
**não** incluem uma linha de repórter «Mundo» e que `reporter=0` devolve vazio —
pelo que nunca misturamos o agregado «Mundo» numa soma de parceiros (o que causaria
dupla contagem). Do lado direto, os totais de produto usam a linha «Mundo»
(`partnerCode=0`) do próprio reporte do país.

## Cobertura e designações

- **Período:** 2003–2024 (anual). 2003 é o ano de arranque usado em todo o projeto
  (criação do Fórum de Macau); 2024 é o último ano com cobertura suficiente à data
  de extração.
- **PLP:** os 9 Países de Língua Portuguesa (códigos M49): Angola, Brasil, Cabo
  Verde, Guiné-Bissau, Guiné Equatorial, Moçambique, Portugal, São Tomé e Príncipe,
  Timor-Leste.
- **Designações:** seguindo a prática do projeto, as regiões especiais da China
  aparecem como **Macau (RAEM)** e **Hong Kong (RAEHK)**, e «Other Asia, nes» como
  **Taiwan (Prov. China)**.
- **Taiwan não faz parte dos dados públicos deste site.** Sobre o tratamento dos
  dados de Taiwan na base UN Comtrade, ver a nota oficial:
  <https://uncomtrade.org/docs/taiwan-province-of-china-trade-data/>.
- Os nomes de parceiros aparecem em português (dicionário curado pelo projeto, com
  *fallback* para o nome inglês do Comtrade); os produtos usam rótulos curtos em
  português quando disponíveis, com o código HS6 sempre visível.

## Produtos (HS-AG6)

O detalhe de produtos usa o nível **HS-AG6** (6 dígitos, o mais fino harmonizado
internacionalmente). Nunca misturamos níveis de agregação (HS2/HS4/HS6) nem códigos
de modo de transporte/alfândega na mesma soma — isso duplicaria valores. Nota: a
soma do detalhe AG6 pode ficar abaixo do total «TOTAL» declarado, devido a
supressões por confidencialidade na fonte.

## Rankings, quotas e concorrência

- **Principais parceiros/produtos (D6/D7):** top 10 por ano e base; a quota é
  calculada sobre o total mundial do ano na mesma base.
- **Produto × parceiro (D8):** os 25 produtos mais importantes do período × 8
  parceiros por produto/ano; a quota é sobre o total desse produto-ano.
- **Concorrência (D9/D10; secções 2.4/3.4 dos perfis):** para os 5 principais
  parceiros diretos × 8 principais produtos diretos, a posição do país entre os
  fornecedores de cada cliente (2.4, a partir das importações do cliente) ou entre
  os clientes de cada fornecedor (3.4, a partir das exportações do fornecedor).
  Mostram-se os 5 principais concorrentes por mercado, além do próprio país.
  Os parceiros são restritos a repórteres válidos da API (pseudo-parceiros como
  «Bunkers» não podem ser consultados como repórteres).
- As posições usam *ranking denso*: valores empatados partilham a mesma posição.
- Registos de valor inferior a 1 USD (a fonte contém valores fracionários) são
  omitidos das tabelas detalhadas.

## Validação

- **Testes de contrato automáticos** (`pytest`, offline): mais de 120 verificações
  de esquema, domínios e coerência interna correm sobre cada nova extração antes de
  ser publicada (ex.: volume = exportações + importações; quotas entre 0 e 100%;
  unicidade das chaves ano × parceiro × base).
- **Guarda contra truncagem:** cada resposta da API é comparada com o limite de
  registos por chamada; blocos suspeitos de truncagem são refeitos ano a ano.
- **Verificações pontuais** ao longo do desenvolvimento: comparação com os quadros
  do Fórum de Macau e com o World Bank WITS, e confronto direto/espelho de fluxos
  agregados.

## Limitações

- Valores em **USD correntes** — sem deflação; comparações temporais refletem também
  preços e câmbio.
- A base espelho não substitui a direta: são leituras complementares.
- Países com reporte direto fraco (ex.: Timor-Leste, com vários anos sem reporte
  AG6) têm a vista espelho como referência principal nos respetivos perfis.
- A cobertura da concorrência (D9/D10) limita-se aos principais parceiros/produtos
  diretos; mercados fora desse conjunto não aparecem.

## Atualização

Os dados são reextraídos manualmente quando chegam novas *vintages* do UN Comtrade
(normalmente revisões anuais). Cada ficheiro `.meta.json` regista a data de geração;
a cache local (90 dias) torna as reextrações incrementais.

## Como citar

Sugestão de citação:

> Observatório China–PLP Comércio. Dados: United Nations Comtrade Database
> (comtradeplus.un.org), extraídos via API em [ver `generated_at` de cada conjunto];
> tratamento e visualização: projeto cipf-comtrade, Universidade Politécnica de
> Macau. <https://joaquimrcarvalho.github.io/cipf-comtrade/> (acedido em …).

Cite também a fonte primária quando apropriado: *United Nations Comtrade Database*
(<https://comtradeplus.un.org>).

## Reproduzir

Todo o pipeline é aberto: repositório
[github.com/joaquimrcarvalho/cipf-comtrade](https://github.com/joaquimrcarvalho/cipf-comtrade)
— blocos de notas de análise (com documentação própria em `*_README.md`), o módulo
`comtradetools.py` (manual em `docs/comtradetools.md`), os *scripts* de extração do
site em `site/scripts/` e os testes em `tests/`. Para reextrair é necessária uma
chave gratuita da API UN Comtrade (sem chave, a API pública limita as respostas a
500 registos, o que pode viciar agregados).
