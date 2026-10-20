// Números (1 a 4) com Counter animado e a fonte de cada um em mono, pequena, embaixo (D-18).
import React from "react";
import { theme } from "../theme";
import { Counter } from "../components/Counter";
import { Stagger } from "../components/Stagger";
import { CenaProps, Moldura, slideDe, TituloDeSecao, useMedidas } from "./Slide";

export const Estatisticas: React.FC<CenaProps> = ({ deck, index }) => {
  const s = slideDe(deck, index, "estatisticas");
  const { u } = useMedidas();
  const n = s.numeros.length;
  const tamanho = n === 1 ? 200 : n === 2 ? 150 : 110;
  return (
    <Moldura deck={deck} index={index}>
      <TituloDeSecao texto={s.titulo} />
      <Stagger
        startAt={20}
        offset={6}
        variant="rise"
        containerStyle={{ display: "grid", gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))`, gap: 32 * u }}
        items={s.numeros.map((num, i) => (
          <div key={i} style={{ padding: 36 * u, borderRadius: 24 * u, background: theme.colors.surface, border: `1px solid ${theme.colors.line}` }}>
            <div style={{ fontSize: tamanho * u, lineHeight: 1, letterSpacing: -2 }}>
              <Counter target={num.valor} delay={24 + i * 6} suffix={num.sufixo ?? ""} />
            </div>
            <p style={{ margin: `${18 * u}px 0 0`, fontFamily: theme.fonts.displayAlt, fontWeight: 600, fontSize: 30 * u, textTransform: "uppercase", letterSpacing: 1 }}>{num.rotulo}</p>
            <p style={{ margin: `${10 * u}px 0 0`, fontFamily: theme.fonts.mono, fontSize: 18 * u, color: theme.colors.textSoft }}>fonte: {num.fonte}</p>
          </div>
        ))}
      />
    </Moldura>
  );
};
