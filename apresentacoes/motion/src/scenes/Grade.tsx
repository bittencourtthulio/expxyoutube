// Grade de cartões (3 a 6): cada cartão entra escalonado com variante alternada.
import React from "react";
import { theme } from "../theme";
import { Stagger } from "../components/Stagger";
import { CenaProps, Moldura, slideDe, TituloDeSecao, useMedidas } from "./Slide";

export const Grade: React.FC<CenaProps> = ({ deck, index }) => {
  const s = slideDe(deck, index, "grade");
  const { u } = useMedidas();
  const cols = s.itens.length <= 4 ? Math.min(s.itens.length, 4) : 3;
  return (
    <Moldura deck={deck} index={index}>
      <TituloDeSecao texto={s.titulo} />
      <Stagger
        startAt={22}
        offset={5}
        containerStyle={{ display: "grid", gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`, gap: 24 * u }}
        itemStyle={{ height: "100%" }}
        items={s.itens.map((item, i) => (
          <div
            key={i}
            style={{
              height: "100%",
              boxSizing: "border-box",
              padding: 32 * u,
              borderRadius: 20 * u,
              background: theme.colors.surface,
              border: `1px solid ${theme.colors.line}`,
              borderTop: `4px solid ${theme.colors.accent}`,
            }}
          >
            <p style={{ margin: 0, fontFamily: theme.fonts.mono, fontSize: 20 * u, color: theme.colors.textSoft, letterSpacing: 2 }}>{String(i + 1).padStart(2, "0")}</p>
            <h3 style={{ margin: `${12 * u}px 0 ${14 * u}px`, fontFamily: theme.fonts.displayAlt, fontWeight: 700, fontSize: 36 * u, lineHeight: 1.1 }}>{item.titulo}</h3>
            <p style={{ margin: 0, fontFamily: theme.fonts.body, fontSize: 26 * u, lineHeight: 1.35, color: theme.colors.textSoft }}>{item.texto}</p>
          </div>
        ))}
      />
    </Moldura>
  );
};
