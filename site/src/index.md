# China–PLP: comércio em números

<div style="background: var(--theme-background-alt); border-radius: 8px; padding: 1rem 1.25rem; margin: 1.5rem 0;">
  <strong>🚧 Em construção — Fase 0.</strong>
  Este é o esqueleto do futuro observatório de dados do comércio entre a China e os
  Países de Língua Portuguesa (PLP), gerado com
  <a href="https://observablehq.com/framework/">Observable Framework</a> a partir do
  projeto <a href="https://github.com/joaquimrcarvalho/cipf-comtrade">cipf-comtrade</a>.
  Os dados e as visualizações interativas serão adicionados nas próximas fases.
</div>

## O que vai encontrar aqui

| Secção | Conteúdo planeado |
|---|---|
| [Trocas China–PLP](/china-plp) | Exportações, importações, volume de trocas e saldo comercial China ↔ PLP, 2003–presente, com tabelas ao estilo do Fórum Macau |
| [Macau–PLP](/macau) | Trocas comerciais de Macau com os PLP e o papel de Macau como plataforma |
| [Hong Kong–PLP](/hong-kong) | Trocas comerciais de Hong Kong com os PLP |
| [Taiwan–PLP](/taiwan) | Trocas comerciais de Taiwan com os PLP |
| [Perfis por país](/perfis) | Perfil comercial de cada PLP: balança, principais parceiros, principais produtos (HS-AG6), clientes e fornecedores |
| [Metodologia e fontes](/metodologia) | Fonte UN Comtrade, valores diretos vs. simétricos (espelho), validação, como citar |
| [Dados abertos](/dados) | Descarregamento de todos os conjuntos de dados em CSV |

## Fonte dos dados

Todos os valores provêm da base de dados [UN Comtrade](https://comtradeplus.un.org/)
(Nações Unidas), obtidos via API com o módulo
[`comtradetools.py`](https://github.com/joaquimrcarvalho/cipf-comtrade) e validados
contra os quadros publicados pelo
[Fórum para a Cooperação Económica e Comercial entre a China e os Países de Língua
Portuguesa (Fórum Macau)](https://www.forumchinaplp.org.mo/).
