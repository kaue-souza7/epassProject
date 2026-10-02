export const FOLHA_TEMPLATE = {
  imageWidth: 600,
  imageHeight: 800,

  maxQuestoes: 15,

  alternativas: ["A", "B", "C", "D", "E"] as const,

  circulos: Array.from({ length: 15 }, (_, i) =>
    Array.from({ length: 5 }, (_, j) => ({
      questao: i + 1,
      alternativa: ["A", "B", "C", "D", "E"][j],
      cx: Math.round(148 + j * 57),
      cy: Math.round(128 + i * 40),
      raio: 11,
      raioAmostragem: 5,
    }))
  ).flat(),

  marcadores: [
    { name: "TL", cx: 34, cy: 86 },
    { name: "TR", cx: 566, cy: 86 },
    { name: "BL", cx: 34, cy: 750 },
    { name: "BR", cx: 566, cy: 750 },
  ],
} as const;
