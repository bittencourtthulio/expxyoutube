// As quatro camadas de fundo/acabamento da pilha de cinco (regra 5): fundo com textura -> [conteúdo]
// -> Grade -> Grain -> Vignette. Diferente do template 4:5, o BgMesh escala com o quadro (16:9 ou
// qualquer outro): os blobs são proporcionais a width/height e não ficam presos à borda esquerda.
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { clarear, rgba, theme } from "../theme";

export const BgMesh: React.FC<{ accent?: string }> = ({ accent }) => {
  const frame = useCurrentFrame();
  const cor = accent ?? theme.colors.accent;
  const cor2 = accent ? clarear(accent, 0.18) : theme.colors.accent2;
  const { width, height } = useVideoConfig();
  const d1 = Math.sin(frame / 55) * width * 0.03;
  const d2 = Math.cos(frame / 70) * width * 0.025;
  const grande = Math.round(Math.max(width, height) * 0.7);
  const medio = Math.round(Math.max(width, height) * 0.5);
  return (
    <AbsoluteFill style={{ background: theme.colors.bg }}>
      <div
        style={{
          position: "absolute",
          width: grande,
          height: grande,
          borderRadius: "50%",
          top: -grande * 0.42,
          left: -grande * 0.18 + d1,
          filter: "blur(70px)",
          background: `radial-gradient(circle, ${rgba(cor, 0.14)}, transparent 60%)`,
        }}
      />
      <div
        style={{
          position: "absolute",
          width: medio,
          height: medio,
          borderRadius: "50%",
          bottom: -medio * 0.45,
          right: -medio * 0.22 - d2,
          filter: "blur(90px)",
          background: `radial-gradient(circle, ${rgba(cor2, 0.1)}, transparent 62%)`,
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `linear-gradient(${theme.colors.line} 1px, transparent 1px), linear-gradient(90deg, ${theme.colors.line} 1px, transparent 1px)`,
          backgroundSize: `${Math.round(width / 24)}px ${Math.round(width / 24)}px`,
          opacity: 0.35,
          maskImage: "radial-gradient(ellipse at center, black 30%, transparent 78%)",
          WebkitMaskImage: "radial-gradient(ellipse at center, black 30%, transparent 78%)",
        }}
      />
    </AbsoluteFill>
  );
};

// Camada de cor sobre o conteúdo. Renderiza acima do conteúdo, abaixo do grão.
export const Grade: React.FC<{ opacity?: number; accent?: string }> = ({ opacity = 0.12, accent }) => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    <AbsoluteFill style={{ backgroundColor: accent ?? theme.colors.accent, mixBlendMode: "soft-light", opacity }} />
    <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.12), transparent 26%, transparent 74%, rgba(0,0,0,0.22))" }} />
  </AbsoluteFill>
);

// Grão procedural, sem asset. Opacidade baixa em multiply.
export const Grain: React.FC = () => {
  const frame = useCurrentFrame();
  const noise = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='220' height='220'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='220' height='220' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E")`;
  return (
    <AbsoluteFill
      style={{
        pointerEvents: "none",
        backgroundImage: noise,
        backgroundSize: "220px",
        backgroundPosition: `${(frame * 7) % 220}px ${(frame * 13) % 220}px`,
        opacity: 0.05,
        mixBlendMode: "multiply",
      }}
    />
  );
};

export const Vignette: React.FC = () => (
  <AbsoluteFill style={{ pointerEvents: "none", background: "radial-gradient(ellipse at center, transparent 56%, rgba(0,0,0,0.24) 100%)" }} />
);

/** As três camadas de acabamento, na ordem certa. Use no fim de toda cena. */
export const Finish: React.FC<{ gradeOpacity?: number; accent?: string }> = ({ gradeOpacity, accent }) => (
  <>
    <Grade opacity={gradeOpacity} accent={accent} />
    <Grain />
    <Vignette />
  </>
);
