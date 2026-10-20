// Antes/depois, A contra B: coluna apagada à esquerda, coluna da marca à direita.
import React from "react";
import { theme } from "../theme";
import { Entrance } from "../components/Entrance";
import { Stagger } from "../components/Stagger";
import { CenaProps, Moldura, slideDe, TituloDeSecao, useMedidas } from "./Slide";
import { Coluna as ColunaTipo } from "../deck";

const Coluna: React.FC<{ col: ColunaTipo; destaque: boolean; startAt: number; u: number }> = ({ col, destaque, startAt, u }) => (
  <div
    style={{
      padding: 40 * u,
      borderRadius: 24 * u,
      background: destaque ? theme.colors.surface : "transparent",
      border: `1px solid ${destaque ? theme.colors.accent : theme.colors.line}`,
      boxShadow: destaque ? `0 0 0 1px ${theme.colors.line}` : undefined,
    }}
  >
    <h3 style={{ margin: 0, marginBottom: 28 * u, fontFamily: theme.fonts.displayAlt, fontWeight: 700, fontSize: 40 * u, color: destaque ? theme.colors.accent : theme.colors.textSoft, textTransform: "uppercase", letterSpacing: 1 }}>
      {col.titulo}
    </h3>
    <Stagger
      startAt={startAt}
      offset={5}
      variant="rise"
      containerStyle={{ display: "flex", flexDirection: "column", gap: 18 * u }}
      items={col.itens.map((item, i) => (
        <p key={i} style={{ margin: 0, display: "flex", gap: 18 * u, alignItems: "baseline", fontFamily: theme.fonts.body, fontSize: 30 * u, lineHeight: 1.3, color: destaque ? theme.colors.text : theme.colors.textSoft }}>
          <span style={{ width: 12 * u, height: 12 * u, flex: "none", background: destaque ? theme.colors.accent : theme.colors.textSoft, transform: "translateY(-2px)", opacity: destaque ? 1 : 0.6 }} />
          {item}
        </p>
      ))}
    />
  </div>
);

export const Comparacao: React.FC<CenaProps> = ({ deck, index }) => {
  const s = slideDe(deck, index, "comparacao");
  const { u } = useMedidas();
  return (
    <Moldura deck={deck} index={index}>
      <TituloDeSecao texto={s.titulo} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 * u }}>
        <Entrance delay={18} variant="right">
          <Coluna col={s.esquerda} destaque={false} startAt={30} u={u} />
        </Entrance>
        <Entrance delay={24} variant="left">
          <Coluna col={s.direita} destaque startAt={36} u={u} />
        </Entrance>
      </div>
    </Moldura>
  );
};
