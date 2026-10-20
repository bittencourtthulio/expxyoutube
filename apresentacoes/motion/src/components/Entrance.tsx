// Entrada padrão: opacidade + translate + escala juntas (regra 2 de motion/tecnica.md). Nunca fade puro.
// Portado do template CANAL (sistema de apresentações .claude/assets/motion); sem useExit: o slide ao vivo segura o
// último frame em vez de sair (D-08).
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";

export type EntranceVariant = "rise" | "fall" | "left" | "right" | "pop";

const VARIANTS: Record<
  EntranceVariant,
  { axis: "x" | "y"; distance: number; from: number; config: keyof typeof theme.spring }
> = {
  rise: { axis: "y", distance: 40, from: 0.94, config: "smooth" },
  fall: { axis: "y", distance: -40, from: 0.94, config: "smooth" },
  left: { axis: "x", distance: 90, from: 0.96, config: "snappy" },
  right: { axis: "x", distance: -90, from: 0.96, config: "snappy" },
  pop: { axis: "y", distance: 14, from: 0.62, config: "bouncy" }, // só palavra de impacto
};

/** Alterna variantes sem repetir em sequência. Use o índice do item. */
export const variantFor = (i: number): EntranceVariant => {
  const cycle: EntranceVariant[] = ["rise", "left", "fall", "right"];
  return cycle[i % cycle.length];
};

export const Entrance: React.FC<{
  delay?: number;
  rise?: number;
  variant?: EntranceVariant;
  config?: keyof typeof theme.spring;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ delay = 0, rise, variant = "rise", config, style, children }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const v = VARIANTS[variant];
  const p = spring({ frame: frame - delay, fps, config: theme.spring[config ?? v.config] });
  const distance = rise ?? v.distance;
  const shift = interpolate(p, [0, 1], [distance, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const move = v.axis === "y" ? `translateY(${shift}px)` : `translateX(${shift}px)`;
  return (
    <div
      style={{
        opacity: p,
        transform: `${move} scale(${interpolate(p, [0, 1], [v.from, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })})`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};
