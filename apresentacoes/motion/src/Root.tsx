// Uma composição por slide do deck recebido em input props (apresentacao.py render passa o deck.json
// inteiro). Sem input props (Studio aberto à mão), registra o DECK_EXEMPLO. A cor da marca é aplicada
// aqui, antes de qualquer cena, e vale para todo worker de render (o Root roda em cada um).
import React from "react";
import { Composition, getInputProps } from "remotion";
import { ALTURA, DECK_EXEMPLO, Deck, FPS, FRAMES_POR_SLIDE, LARGURA, Slide } from "./deck";
import { aplicarMarca } from "./theme";
import { Titulo } from "./scenes/Titulo";
import { Declaracao } from "./scenes/Declaracao";
import { Grade } from "./scenes/Grade";
import { Comparacao } from "./scenes/Comparacao";
import { Etapas } from "./scenes/Etapas";
import { Estatisticas } from "./scenes/Estatisticas";
import { Fluxo } from "./scenes/Fluxo";
import { Screenshot } from "./scenes/Screenshot";
import { Cta } from "./scenes/Cta";
import { CenaProps } from "./scenes/Slide";

// Um tipo do deck.json (D-46) -> uma cena 16:9.
const CENAS: Record<Slide["tipo"], React.FC<CenaProps>> = {
  titulo: Titulo,
  declaracao: Declaracao,
  grade: Grade,
  comparacao: Comparacao,
  etapas: Etapas,
  estatisticas: Estatisticas,
  fluxo: Fluxo,
  screenshot: Screenshot,
  cta: Cta,
};

const deckDeEntrada = (): Deck => {
  const props = getInputProps() as Partial<Deck>;
  if (props && Array.isArray(props.slides) && props.slides.length > 0 && props.marca) {
    return props as Deck;
  }
  return DECK_EXEMPLO;
};

export const RemotionRoot: React.FC = () => {
  const deck = deckDeEntrada();
  aplicarMarca(deck.marca.cor, deck.marca.cor_2);
  return (
    <>
      {deck.slides.map((slide, i) => (
        <Composition
          key={`slide-${i + 1}`}
          id={`slide-${i + 1}`}
          component={CENAS[slide.tipo] ?? Titulo}
          durationInFrames={FRAMES_POR_SLIDE}
          fps={FPS}
          width={LARGURA}
          height={ALTURA}
          defaultProps={{ deck, index: i }}
        />
      ))}
    </>
  );
};
