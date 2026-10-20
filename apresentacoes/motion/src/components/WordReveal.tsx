// Título palavra por palavra. `<b>palavra</b>` vira destaque na cor da marca. Envolva a palavra-chave,
// nunca a frase (regra 70/20/10). `fontSize` é TETO: a fonte encolhe até a palavra mais longa caber em
// `withinWidth` (trava de estouro do template CANAL). `validateFontIsLoaded` transforma "fonte não
// carregou" em erro de render em vez de serifada silenciosa.
import React from "react";
import { fitText } from "@remotion/layout-utils";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";

type Token = { text: string; accent: boolean };

export const parseDestaque = (raw: string): Token[] => {
  const parts = raw.split(/(<b>.*?<\/b>)/g).filter(Boolean);
  const tokens: Token[] = [];
  for (const part of parts) {
    const match = part.match(/^<b>(.*?)<\/b>$/);
    const chunk = match ? match[1] : part;
    const accent = Boolean(match);
    for (const word of chunk.split(" ").filter(Boolean)) {
      tokens.push({ text: word, accent });
    }
  }
  return tokens;
};

export const WordReveal: React.FC<{
  text: string;
  withinWidth: number;
  fontSize: number;
  delay?: number;
  per?: number;
  fontFamily?: string;
  accentColor?: string;
  style?: React.CSSProperties;
}> = ({ text, withinWidth, fontSize, delay = 0, per = 3, fontFamily, accentColor, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tokens = parseDestaque(text);
  const family = fontFamily ?? theme.fonts.display;

  const longest = tokens.reduce((acc, token) => (token.text.length > acc.length ? token.text : acc), "");
  const fitted = fitText({
    text: longest,
    withinWidth,
    fontFamily: family,
    textTransform: (style?.textTransform as "uppercase" | undefined) ?? "none",
    validateFontIsLoaded: true,
  });
  const size = Math.min(fontSize, fitted.fontSize);

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "0.26em",
        fontFamily: family,
        color: theme.colors.text,
        ...style,
        fontSize: size,
        maxWidth: withinWidth,
      }}
    >
      {tokens.map((token, i) => {
        const p = spring({ frame: frame - (delay + i * per), fps, config: theme.spring.snappy });
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              opacity: p,
              color: token.accent ? accentColor ?? theme.colors.accent : undefined,
              transform: `translateY(${interpolate(p, [0, 1], [30, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}px)`,
            }}
          >
            {token.text}
          </span>
        );
      })}
    </div>
  );
};
