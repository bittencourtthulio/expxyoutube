// Ken Burns obrigatório em toda imagem estática (regra 6): `slow` atrás de texto, `fast` quando a
// imagem é o assunto. Alterne `dir` entre slides consecutivos para o conjunto não pulsar igual.
import React from "react";
import { Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";

export const ZOOM = {
  slow: { from: 1.0, to: 1.03 },
  normal: { from: 1.02, to: 1.06 },
  fast: { from: 1.0, to: 1.1 },
} as const;

export const KenBurns: React.FC<{
  src: string;
  speed?: keyof typeof ZOOM;
  dir?: 1 | -1;
  panPx?: number;
  style?: React.CSSProperties;
}> = ({ src, speed = "normal", dir = 1, panPx = -20, style }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const range = ZOOM[speed];
  const from = dir > 0 ? range.from : range.to;
  const to = dir > 0 ? range.to : range.from;
  const opts = { easing: theme.ease.inOut, extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };
  const scale = interpolate(frame, [0, durationInFrames], [from, to], opts);
  // Mesma curva no pan e no zoom: sem isso os dois movimentos brigam e a imagem escorrega.
  const pan = interpolate(frame, [0, durationInFrames], [0, panPx * dir], opts);
  return (
    <Img
      src={src.startsWith("http") || src.startsWith("data:") ? src : staticFile(src)}
      style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${scale}) translateX(${pan}px)`, ...style }}
    />
  );
};

/** Moldura de marca: a imagem fica recuada sobre um fundo da paleta; a moldura é o fundo com textura. */
export const PaddedImage: React.FC<{
  src: string;
  bg?: string;
  padPct?: number;
  radius?: number;
  speed?: keyof typeof ZOOM;
  dir?: 1 | -1;
}> = ({ src, bg = theme.colors.bgSoft, padPct = 0.08, radius = 24, speed = "slow", dir = 1 }) => {
  const { width, height } = useVideoConfig();
  const padX = Math.round(width * padPct);
  const padY = Math.round(height * padPct);
  return (
    <div style={{ position: "absolute", inset: 0, backgroundColor: bg }}>
      <div style={{ position: "absolute", top: padY, left: padX, right: padX, bottom: padY, borderRadius: radius, overflow: "hidden" }}>
        <KenBurns src={src} speed={speed} dir={dir} />
      </div>
    </div>
  );
};
