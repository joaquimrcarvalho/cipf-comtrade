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

// Measure selector for Observable Inputs: Map of LABEL → column name.
// (Inputs uses Map keys as the displayed labels and values as the selection.)
export const MEASURES = new Map([
  ["Trocas comerciais", "trade_volume"],
  ["Exportações", "exports"],
  ["Importações", "imports"],
  ["Saldo comercial", "balance"]
]);

// Reverse lookup: column name → pt label
export const MEASURE_LABEL = Object.fromEntries([...MEASURES].map(([l, v]) => [v, l]));
