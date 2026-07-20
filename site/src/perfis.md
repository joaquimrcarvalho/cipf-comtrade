# Perfis por país

Perfil comercial de cada País de Língua Portuguesa, espelhando a estrutura do bloco de
notas `country_trade_profile.ipynb`:

1. **Balança comercial** — valores diretos vs. simétricos (espelho);
2. **Exportações** — principais clientes, principais produtos (HS-AG6), quem compra o quê;
3. **Importações** — principais fornecedores, principais produtos, dependências.

```js
import {formatUSD} from "./components/format.js";

const paises = [
  {slug: "angola", nome: "Angola"},
  {slug: "brasil", nome: "Brasil"},
  {slug: "cabo-verde", nome: "Cabo Verde"},
  {slug: "guine-bissau", nome: "Guiné-Bissau"},
  {slug: "guine-equatorial", nome: "Guiné Equatorial"},
  {slug: "mocambique", nome: "Moçambique"},
  {slug: "portugal", nome: "Portugal"},
  {slug: "sao-tome-e-principe", nome: "São Tomé e Príncipe"},
  {slug: "timor-leste", nome: "Timor-Leste"}
];
// FileAttachment exige um caminho literal (análise estática do Framework) —
// nada de template strings; ficheiros em falta são tolerados com try/catch.
const d5files = {
  "angola": FileAttachment("data/angola_trade_balance_2003-2024.csv"),
  "brasil": FileAttachment("data/brasil_trade_balance_2003-2024.csv"),
  "cabo-verde": FileAttachment("data/cabo-verde_trade_balance_2003-2024.csv"),
  "guine-bissau": FileAttachment("data/guine-bissau_trade_balance_2003-2024.csv"),
  "guine-equatorial": FileAttachment("data/guine-equatorial_trade_balance_2003-2024.csv"),
  "mocambique": FileAttachment("data/mocambique_trade_balance_2003-2024.csv"),
  "portugal": FileAttachment("data/portugal_trade_balance_2003-2024.csv"),
  "sao-tome-e-principe": FileAttachment("data/sao-tome-e-principe_trade_balance_2003-2024.csv"),
  "timor-leste": FileAttachment("data/timor-leste_trade_balance_2003-2024.csv")
};
const resumos = await Promise.all(paises.map(async (p) => {
  try {
    const d5 = await d5files[p.slug].csv({typed: true});
    // último ano com volume > 0; prefere base direta, cai para espelho
    let rows = d5.filter((d) => d.basis === "direct" && d.trade_volume > 0);
    let base = "direta";
    if (!rows.length) {
      rows = d5.filter((d) => d.basis === "mirror" && d.trade_volume > 0);
      base = "espelho";
    }
    const latestYear = rows.length ? Math.max(...rows.map((d) => d.year)) : null;
    const latest = rows.find((d) => d.year === latestYear);
    return {...p, latestYear, base, volume: latest?.trade_volume ?? null,
            exports: latest?.exports ?? null, imports: latest?.imports ?? null,
            disponivel: true};
  } catch {
    return {...p, latestYear: null, volume: null, exports: null, imports: null,
            disponivel: false};
  }
}));
const ordenados = [...resumos].sort((a, b) => b.disponivel - a.disponivel);
```

```js
display(html`<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 0.9rem; margin: 1.25rem 0;">
  ${ordenados.map((p) => p.disponivel ? html`
    <a href="/perfis/${p.slug}" style="text-decoration: none; color: inherit;">
      <div style="background: var(--theme-background-alt); border-radius: 8px; padding: 1rem 1.15rem; height: 100%;">
        <div style="font-weight: 600; font-size: 1.05rem;">${p.nome}</div>
        <div style="font-size: 1.35rem; font-weight: 600; margin: 0.3rem 0 0.1rem;">${formatUSD(p.volume)}</div>
        <div style="font-size: 0.78rem; color: var(--theme-foreground-muted)">
          volume de trocas com o mundo, ${p.latestYear} (base ${p.base})
        </div>
        <div style="font-size: 0.78rem; color: var(--theme-foreground-faint); margin-top: 0.35rem;">
          X ${formatUSD(p.exports)} · M ${formatUSD(p.imports)}
        </div>
      </div>
    </a>` : html`
    <div style="background: var(--theme-background-alt); border-radius: 8px; padding: 1rem 1.15rem; height: 100%; opacity: 0.55;">
      <div style="font-weight: 600; font-size: 1.05rem;">${p.nome}</div>
      <div style="font-size: 0.85rem; color: var(--theme-foreground-muted); margin-top: 0.3rem;">
        dados a carregar — disponível em breve
      </div>
    </div>`)}
</div>`);
```

<div style="font-size: 0.85rem; color: var(--theme-foreground-muted)">
  Valores em USD correntes, no último ano com dados (base indicada em cada cartão). A análise China ↔ PLP
  está em <a href="/china-plp">Trocas China–PLP</a>; o papel das plataformas em
  <a href="/macau">Macau (RAEM)</a> e <a href="/hong-kong">Hong Kong (RAEHK)</a>.
</div>
