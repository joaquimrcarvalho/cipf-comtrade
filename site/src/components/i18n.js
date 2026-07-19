// UI string dictionary (pt-PT) — single source of site copy for a future EN mirror.
// Spec: docs/SITE_SPECS.md §6.4.
export const L = {
  ano: "Ano",
  pais: "País",
  medida: "Medida",
  base: "Base de dados",
  direct: "Reportado pelo emissor (direto)",
  mirror: "Reportado pelos parceiros (espelho)",
  logScale: "Escala logarítmica",
  fonte: "Fonte: UN Comtrade, extração e análise próprias",
  downloadCSV: "Descarregar CSV",
  downloadMeta: "Metadados (JSON)"
};

// Measure selector: column name → pt label
export const MEASURES = new Map([
  ["trade_volume", "Trocas comerciais"],
  ["exports", "Exportações"],
  ["imports", "Importações"],
  ["balance", "Saldo comercial"]
]);

export const MEASURE_LABEL = Object.fromEntries(MEASURES);
