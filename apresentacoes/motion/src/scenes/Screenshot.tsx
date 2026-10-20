// Evidência de UI: a captura ocupa o slide com Ken Burns lento numa moldura. Sem imagem (D-48), a
// moldura fica vazia com a legenda dentro; nunca monta <Img> com arquivo que não existe.
import React from "react";
import { theme } from "../theme";
import { Entrance } from "../components/Entrance";
import { KenBurns } from "../components/KenBurns";
import { CenaProps, Moldura, slideDe, useMedidas } from "./Slide";

export const Screenshot: React.FC<CenaProps> = ({ deck, index }) => {
  const s = slideDe(deck, index, "screenshot");
  const { u, inner, altura } = useMedidas();
  const alturaMoldura = altura * 0.66;
  return (
    <Moldura deck={deck} index={index} gradeOpacity={0.06}>
      <Entrance delay={4} rise={20}>
        <h2 style={{ margin: 0, marginBottom: 22 * u, fontFamily: theme.fonts.displayAlt, fontWeight: 700, fontSize: 48 * u, lineHeight: 1.1 }}>{s.titulo}</h2>
      </Entrance>
      <Entrance delay={14} rise={40} config="smooth">
        <div
          style={{
            width: inner,
            height: alturaMoldura,
            borderRadius: 22 * u,
            overflow: "hidden",
            background: theme.colors.bgSoft,
            border: `1px solid ${theme.colors.line}`,
            boxShadow: `0 30px 80px rgba(0,0,0,0.45), 0 0 0 1px ${theme.colors.line}`,
            position: "relative",
          }}
        >
          <div style={{ height: 34 * u, background: theme.colors.surface2, display: "flex", alignItems: "center", gap: 8 * u, padding: `0 ${16 * u}px` }}>
            {[0, 1, 2].map((i) => (
              <span key={i} style={{ width: 11 * u, height: 11 * u, borderRadius: "50%", background: i === 0 ? theme.colors.accent : theme.colors.line }} />
            ))}
          </div>
          <div style={{ position: "absolute", top: 34 * u, left: 0, right: 0, bottom: 0 }}>
            {s.imagem ? (
              <KenBurns src={s.imagem} speed="slow" dir={index % 2 === 0 ? 1 : -1} />
            ) : (
              <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: theme.fonts.mono, fontSize: 28 * u, color: theme.colors.textSoft, letterSpacing: 2 }}>
                {s.legenda ?? "captura não disponível"}
              </div>
            )}
          </div>
        </div>
      </Entrance>
      {s.legenda && s.imagem ? (
        <Entrance delay={30} rise={16}>
          <p style={{ margin: `${20 * u}px 0 0`, fontFamily: theme.fonts.mono, fontSize: 24 * u, color: theme.colors.textSoft, letterSpacing: 1 }}>{s.legenda}</p>
        </Entrance>
      ) : null}
    </Moldura>
  );
};
