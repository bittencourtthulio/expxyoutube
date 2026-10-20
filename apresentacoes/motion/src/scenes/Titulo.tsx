// Slide de título: kicker em mono, título em Anton palavra por palavra com o destaque na cor da marca,
// subtítulo em Chakra Petch. Uma linha fina da marca sublinha o bloco (o único brilho é a palavra <b>).
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { Entrance } from "../components/Entrance";
import { WordReveal } from "../components/WordReveal";
import { CenaProps, Moldura, slideDe, useMedidas } from "./Slide";

export const Titulo: React.FC<CenaProps> = ({ deck, index }) => {
  const s = slideDe(deck, index, "titulo");
  const { inner, u } = useMedidas();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const linha = spring({ frame: frame - 30, fps, config: theme.spring.smooth });
  return (
    <Moldura deck={deck} index={index}>
      {s.kicker ? (
        <Entrance delay={4} rise={18}>
          <p style={{ margin: 0, marginBottom: 28 * u, fontFamily: theme.fonts.mono, fontSize: 26 * u, letterSpacing: 4, textTransform: "uppercase", color: theme.colors.accent }}>
            {s.kicker}
          </p>
        </Entrance>
      ) : null}
      <WordReveal text={s.titulo} delay={8} per={3} withinWidth={inner * 0.88} fontSize={138 * u} style={{ lineHeight: 0.98, textTransform: "uppercase" }} />
      <div
        style={{
          marginTop: 30 * u,
          height: 6 * u,
          width: interpolate(linha, [0, 1], [0, 220 * u], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          background: theme.colors.accent,
          borderRadius: 3,
        }}
      />
      {s.subtitulo ? (
        <Entrance delay={36} rise={24}>
          <p style={{ margin: 0, marginTop: 30 * u, fontFamily: theme.fonts.body, fontSize: 40 * u, lineHeight: 1.3, color: theme.colors.textSoft, maxWidth: inner * 0.7 }}>
            {s.subtitulo}
          </p>
        </Entrance>
      ) : null}
    </Moldura>
  );
};
