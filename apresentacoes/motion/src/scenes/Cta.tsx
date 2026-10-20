// CTA final, sempre do Seu Site e sempre no verde CANAL (D-14), independente da marca do deck: a
// cor entra por prop na moldura, no título e no chip, sem mexer no theme. Sem imagem, a moldura vira um cartão
// com a URL grande (D-48).
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { CANAL_ACCENT, theme } from "../theme";
import { Entrance } from "../components/Entrance";
import { KenBurns } from "../components/KenBurns";
import { WordReveal } from "../components/WordReveal";
import { CenaProps, Moldura, slideDe, useMedidas } from "./Slide";

export const Cta: React.FC<CenaProps> = ({ deck, index }) => {
  const s = slideDe(deck, index, "cta");
  const { u, inner, altura } = useMedidas();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const chip = spring({ frame: frame - 40, fps, config: theme.spring.bouncy });
  return (
    <Moldura deck={deck} index={index} marcaTexto="Seu Site" cor={CANAL_ACCENT} gradeOpacity={0.08}>
      <div style={{ display: "grid", gridTemplateColumns: "1.05fr 1fr", gap: 56 * u, alignItems: "center" }}>
        <div>
          <Entrance delay={4} rise={18}>
            <p style={{ margin: 0, marginBottom: 22 * u, fontFamily: theme.fonts.mono, fontSize: 24 * u, letterSpacing: 4, textTransform: "uppercase", color: CANAL_ACCENT }}>
              Próximo passo
            </p>
          </Entrance>
          <WordReveal text={s.titulo} delay={8} per={3} withinWidth={inner * 0.5} fontSize={96 * u} accentColor={CANAL_ACCENT} style={{ lineHeight: 1.0, textTransform: "uppercase" }} />
          {s.texto ? (
            <Entrance delay={30} rise={22}>
              <p style={{ margin: `${26 * u}px 0 0`, fontFamily: theme.fonts.body, fontSize: 32 * u, lineHeight: 1.35, color: theme.colors.textSoft, maxWidth: inner * 0.46 }}>{s.texto}</p>
            </Entrance>
          ) : null}
          <div
            style={{
              display: "inline-block",
              marginTop: 36 * u,
              padding: `${20 * u}px ${34 * u}px`,
              borderRadius: 14 * u,
              background: CANAL_ACCENT,
              color: theme.colors.bg,
              fontFamily: theme.fonts.mono,
              fontSize: 30 * u,
              fontWeight: 500,
              letterSpacing: 1,
              opacity: chip,
              transform: `scale(${interpolate(chip, [0, 1], [0.7, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })})`,
              boxShadow: `0 0 0 1px rgba(34,197,94,0.18), 0 0 32px rgba(34,197,94,0.28)`,
            }}
          >
            {s.url}
          </div>
        </div>
        <Entrance delay={16} variant="left" config="smooth">
          <div
            style={{
              height: altura * 0.62,
              borderRadius: 22 * u,
              overflow: "hidden",
              background: "#0B0B0B",
              border: `1px solid rgba(34,197,94,0.35)`,
              boxShadow: "0 30px 80px rgba(0,0,0,0.5)",
              position: "relative",
              transform: "rotate(-1.5deg)",
            }}
          >
            {s.imagem ? (
              <KenBurns src={s.imagem} speed="slow" dir={-1} panPx={-12} />
            ) : (
              <div style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 18 * u }}>
                <span style={{ fontFamily: theme.fonts.display, fontSize: 92 * u, color: theme.colors.text, letterSpacing: 1 }}>
                  Canal<span style={{ color: CANAL_ACCENT }}>Play</span>
                </span>
                <span style={{ fontFamily: theme.fonts.mono, fontSize: 30 * u, color: theme.colors.textSoft }}>{s.url}</span>
              </div>
            )}
          </div>
        </Entrance>
      </div>
    </Moldura>
  );
};
