// Passo a passo (3 a 5): número grande em mono na cor da marca, título e texto curtos, trilho vertical.
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { Stagger } from "../components/Stagger";
import { CenaProps, Moldura, slideDe, TituloDeSecao, useMedidas } from "./Slide";

export const Etapas: React.FC<CenaProps> = ({ deck, index }) => {
  const s = slideDe(deck, index, "etapas");
  const { u, inner } = useMedidas();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const trilho = spring({ frame: frame - 26, fps, config: theme.spring.smooth });
  const horizontal = s.itens.length >= 4;
  return (
    <Moldura deck={deck} index={index}>
      <TituloDeSecao texto={s.titulo} />
      <div style={{ position: "relative" }}>
        <div
          style={{
            position: "absolute",
            left: horizontal ? 0 : 34 * u,
            top: horizontal ? 34 * u : 0,
            height: horizontal ? 2 : `${interpolate(trilho, [0, 1], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}%`,
            width: horizontal ? `${interpolate(trilho, [0, 1], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}%` : 2,
            background: theme.colors.line,
          }}
        />
        <Stagger
          startAt={24}
          offset={6}
          variant={horizontal ? "rise" : "left"}
          containerStyle={horizontal
            ? { display: "grid", gridTemplateColumns: `repeat(${s.itens.length}, minmax(0, 1fr))`, gap: 28 * u }
            : { display: "flex", flexDirection: "column", gap: 26 * u, maxWidth: inner * 0.8 }}
          items={s.itens.map((item, i) => (
            <div key={i} style={{ display: "flex", flexDirection: horizontal ? "column" : "row", gap: 24 * u, alignItems: "flex-start" }}>
              <span
                style={{
                  flex: "none",
                  width: 70 * u,
                  height: 70 * u,
                  borderRadius: "50%",
                  background: theme.colors.bg,
                  border: `2px solid ${theme.colors.accent}`,
                  color: theme.colors.accent,
                  fontFamily: theme.fonts.mono,
                  fontSize: 30 * u,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {i + 1}
              </span>
              <div>
                <h3 style={{ margin: 0, marginBottom: 10 * u, fontFamily: theme.fonts.displayAlt, fontWeight: 700, fontSize: 36 * u, lineHeight: 1.1 }}>{item.titulo}</h3>
                <p style={{ margin: 0, fontFamily: theme.fonts.body, fontSize: 26 * u, lineHeight: 1.35, color: theme.colors.textSoft }}>{item.texto}</p>
              </div>
            </div>
          ))}
        />
      </div>
    </Moldura>
  );
};
