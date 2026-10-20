// Número animado. Só com número de origem real (o validar-deck exige `fonte`, D-18).
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";

const formata = (valor: number, decimals: number) =>
  valor.toLocaleString("pt-BR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

export const Counter: React.FC<{
  target: number;
  delay?: number;
  decimals?: number;
  suffix?: string;
  style?: React.CSSProperties;
}> = ({ target, delay = 0, decimals, suffix = "", style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const casas = decimals ?? (Number.isInteger(target) ? 0 : 1);
  const p = spring({ frame: frame - delay, fps, config: theme.spring.smooth });
  const value = interpolate(p, [0, 1], [0, target], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <span style={{ fontFamily: theme.fonts.mono, fontVariantNumeric: "tabular-nums", color: theme.colors.accent, ...style }}>
      {formata(value, casas)}
      {suffix}
    </span>
  );
};
