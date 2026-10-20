// Declaração / tese: uma frase grande em Chakra Petch, aspas da marca, atribuição em mono.
import React from "react";
import { theme } from "../theme";
import { Entrance } from "../components/Entrance";
import { WordReveal } from "../components/WordReveal";
import { CenaProps, Moldura, slideDe, useMedidas } from "./Slide";

export const Declaracao: React.FC<CenaProps> = ({ deck, index }) => {
  const s = slideDe(deck, index, "declaracao");
  const { inner, u } = useMedidas();
  return (
    <Moldura deck={deck} index={index}>
      <div style={{ display: "flex", gap: 40 * u, alignItems: "flex-start", maxWidth: inner * 0.92 }}>
        <Entrance delay={2} variant="pop">
          <span style={{ fontFamily: theme.fonts.display, fontSize: 220 * u, lineHeight: 0.7, color: theme.colors.accent, opacity: 0.9 }}>
            “
          </span>
        </Entrance>
        <div>
          <WordReveal
            text={s.texto}
            delay={8}
            per={3}
            withinWidth={inner * 0.78}
            fontSize={82 * u}
            fontFamily={theme.fonts.displayAlt}
            style={{ lineHeight: 1.12, fontWeight: 700 }}
          />
          {s.autor ? (
            <Entrance delay={44} rise={20}>
              <p style={{ margin: 0, marginTop: 36 * u, fontFamily: theme.fonts.mono, fontSize: 26 * u, letterSpacing: 3, textTransform: "uppercase", color: theme.colors.textSoft }}>
                <span style={{ display: "inline-block", width: 40 * u, height: 2, background: theme.colors.line, verticalAlign: "middle", marginRight: 16 * u }} />
                {s.autor}
              </p>
            </Entrance>
          ) : null}
        </div>
      </div>
    </Moldura>
  );
};
