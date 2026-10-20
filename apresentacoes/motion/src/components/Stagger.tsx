// Escalona uma lista (regra 3): 3-6 frames de defasagem, nada entra ao mesmo tempo. Diferente do
// template original, alterna a variante de entrada por item (`variantFor`) para N cartões não
// lerem como template; `variant` fixa uma só quando a cena pede.
import React from "react";
import { Entrance, EntranceVariant, variantFor } from "./Entrance";

export const Stagger: React.FC<{
  items: React.ReactNode[];
  startAt?: number;
  offset?: number;
  variant?: EntranceVariant | "alternada";
  itemStyle?: React.CSSProperties;
  containerStyle?: React.CSSProperties;
}> = ({ items, startAt = 0, offset = 5, variant = "alternada", itemStyle, containerStyle }) => (
  <div style={containerStyle}>
    {items.map((item, i) => (
      <Entrance key={i} delay={startAt + i * offset} variant={variant === "alternada" ? variantFor(i) : variant} style={itemStyle}>
        {item}
      </Entrance>
    ))}
  </div>
);
