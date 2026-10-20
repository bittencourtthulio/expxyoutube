// Moldura comum de todo slide 16:9: pilha de cinco camadas (BgMesh -> conteúdo -> Grade -> Grain ->
// Vignette), cabeçalho com contador `NN / TOTAL` e a marca (ícone só quando o deck traz logo), e o
// conteúdo respirando (regra 7) até o fim: sem saída animada, o último frame fica estático para o
// apresentador falar por cima (D-06, D-08).
import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Deck, Slide } from "../deck";
import { theme } from "../theme";
import { BgMesh, Finish } from "../components/Layers";
import { Entrance } from "../components/Entrance";
import { breathe } from "../components/Timeline";

export type CenaProps = { deck: Deck; index: number };

/** Medidas derivadas do quadro: nada de px fixo calibrado para outro formato. */
export const useMedidas = () => {
  const { width, height } = useVideoConfig();
  const pad = Math.round(width * 0.05);
  return { width, height, pad, inner: width - pad * 2, altura: height - pad * 2, u: width / 1920 };
};

export const Cabecalho: React.FC<{ deck: Deck; index: number; marcaTexto?: string; cor?: string }> = ({ deck, index, marcaTexto, cor }) => {
  const { u } = useMedidas();
  const logo = deck.marca.logo;
  return (
    <Entrance delay={0} rise={16}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontFamily: theme.fonts.mono,
          fontSize: 24 * u,
          color: theme.colors.textSoft,
          letterSpacing: 2,
        }}
      >
        <span>
          {String(index + 1).padStart(2, "0")} / {String(deck.slides.length).padStart(2, "0")}
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 14 * u, color: cor ?? theme.colors.textSoft }}>
          {logo ? (
            <Img src={staticFile(logo)} style={{ width: 36 * u, height: 36 * u, objectFit: "contain", borderRadius: 8 * u }} />
          ) : (
            <span style={{ width: 12 * u, height: 12 * u, borderRadius: "50%", background: cor ?? theme.colors.accent, display: "inline-block" }} />
          )}
          <span style={{ textTransform: "uppercase" }}>{marcaTexto ?? deck.marca.nome}</span>
        </span>
      </div>
    </Entrance>
  );
};

export const Moldura: React.FC<{
  deck: Deck;
  index: number;
  marcaTexto?: string;
  cor?: string;
  gradeOpacity?: number;
  children: React.ReactNode;
}> = ({ deck, index, marcaTexto, cor, gradeOpacity, children }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { pad } = useMedidas();
  return (
    <AbsoluteFill style={{ fontFamily: theme.fonts.displayAlt, color: theme.colors.text }}>
      <BgMesh accent={cor} />
      <AbsoluteFill style={{ padding: pad }}>
        <Cabecalho deck={deck} index={index} marcaTexto={marcaTexto} cor={cor} />
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            transform: `translateY(${breathe(frame, fps, 3, 5)}px)`,
          }}
        >
          {children}
        </div>
      </AbsoluteFill>
      <Finish gradeOpacity={gradeOpacity} accent={cor} />
    </AbsoluteFill>
  );
};

export const slideDe = <T extends Slide["tipo"]>(deck: Deck, index: number, tipo: T) => {
  const s = deck.slides[index];
  if (!s || s.tipo !== tipo) {
    throw new Error(`slide ${index + 1} não é do tipo ${tipo}`);
  }
  return s as Extract<Slide, { tipo: T }>;
};

/** Título de seção (grade, comparação, etapas, estatísticas): tipográfico, sem cartaz. */
export const TituloDeSecao: React.FC<{ texto: string; delay?: number }> = ({ texto, delay = 4 }) => {
  const { inner, u } = useMedidas();
  return (
    <Entrance delay={delay} rise={24}>
      <h2
        style={{
          margin: 0,
          marginBottom: 40 * u,
          fontFamily: theme.fonts.displayAlt,
          fontWeight: 700,
          fontSize: 58 * u,
          lineHeight: 1.08,
          maxWidth: inner * 0.8,
          letterSpacing: -0.5,
        }}
      >
        {texto}
      </h2>
    </Entrance>
  );
};
