// theme.ts: fonte única de cor, fonte e curva de movimento (regra 9 de motion/tecnica.md do sistema de apresentações).
// A paleta base é a CANAL; `aplicarMarca` troca só a cor de destaque (D-12). Os componentes leem
// `theme.colors` em tempo de render, então a troca feita no Root vale para todo slide.
import { Easing } from "remotion";
import { loadedFonts } from "./fonts";

export const CANAL_ACCENT = "#22C55E";

const HEX = /^#[0-9a-fA-F]{6}$/;

const hexParaRgb = (hex: string): [number, number, number] => [
  parseInt(hex.slice(1, 3), 16),
  parseInt(hex.slice(3, 5), 16),
  parseInt(hex.slice(5, 7), 16),
];

const rgbParaHex = (r: number, g: number, b: number) =>
  "#" + [r, g, b].map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("").toUpperCase();

/** Mistura a cor com branco (fator 0 a 1). */
export const clarear = (hex: string, fator: number) => {
  const [r, g, b] = hexParaRgb(hex);
  return rgbParaHex(r + (255 - r) * fator, g + (255 - g) * fator, b + (255 - b) * fator);
};

export const rgba = (hex: string, alpha: number) => {
  const [r, g, b] = hexParaRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

const paletaBase = () => ({
  bg: "#16181A",
  bgSoft: "#1C1F21",
  surface: "#232729",
  surface2: "#2B3033",
  text: "#F2F5F3",
  textSoft: "#A8B0AC",
  line: "rgba(255,255,255,0.10)",
  // Cor herói. No máximo um elemento em brilho por frame.
  accent: CANAL_ACCENT,
  accent2: "#4ADE80",
  accent3: "#86EFAC",
  glow: "rgba(34, 197, 94, 0.35)",
});

export const theme = {
  colors: paletaBase(),
  fonts: loadedFonts,
  ease: {
    out: Easing.bezier(0.16, 1, 0.3, 1), // entradas
    inOut: Easing.bezier(0.83, 0, 0.17, 1), // movimentos contínuos, Ken Burns
    in: Easing.bezier(0.7, 0, 0.84, 0), // só saídas
  },
  spring: {
    snappy: { damping: 14, stiffness: 160, mass: 0.6 },
    smooth: { damping: 20, stiffness: 90, mass: 1 },
    bouncy: { damping: 11, stiffness: 170, mass: 0.7 },
  },
};

/** Aplica a cor da marca do deck. Cor fora de #RRGGBB mantém a CANAL (o validar-deck já barra antes). */
export const aplicarMarca = (cor?: string | null, cor2?: string | null) => {
  const base = paletaBase();
  const accent = cor && HEX.test(cor) ? cor.toUpperCase() : base.accent;
  const accent2 = cor2 && HEX.test(cor2) ? cor2.toUpperCase() : clarear(accent, 0.18);
  Object.assign(theme.colors, base, {
    accent,
    accent2,
    accent3: clarear(accent, 0.45),
    glow: rgba(accent, 0.35),
  });
  return theme.colors;
};
