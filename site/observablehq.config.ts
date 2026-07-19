// Observable Framework configuration
// Spec: docs/SITE_SPECS.md (§6 site structure, §6.2 visual language)
export default {
  title: "China–PLP Comércio",
  root: "src",

  // Sidebar navigation (§6.1 information architecture)
  pages: [
    {name: "Início", path: "/"},
    {name: "Trocas China–PLP", path: "/china-plp"},
    {name: "Macau (RAEM)–PLP", path: "/macau"},
    {name: "Hong Kong (RAEHK)–PLP", path: "/hong-kong"},
    {name: "Perfis por país", path: "/perfis"},
    {name: "Metodologia e fontes", path: "/metodologia"},
    {name: "Dados abertos", path: "/dados"}
  ],

  // Light theme, table of contents on content pages
  toc: true,
  pager: true,
  search: true,

  head: /* html */ `
    <meta name="description" content="Comércio entre a China e os Países de Língua Portuguesa — dados UN Comtrade, visualização interativa.">
  `,

  header: /* html */ `
    <a href="/" style="font-weight: 600">China–PLP Comércio</a>
  `,

  footer: /* html */ `
    <hr/>
    <div style="font-size: 0.85rem; color: var(--theme-foreground-muted)">
      Fonte: <a href="https://comtradeplus.un.org/">UN Comtrade</a>, extração e análise próprias ·
      <a href="https://github.com/joaquimrcarvalho/cipf-comtrade">Projeto cipf-comtrade</a> ·
      Joaquim Carvalho, Universidade Politécnica de Macau
    </div>
  `
};
