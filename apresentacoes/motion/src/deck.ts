// Tipos do deck.json: contrato entre apresentacao.py e este projeto (D-46; espelho de tests/decks.py).
export type Marca = {
  nome: string;
  cor: string;
  cor_2?: string | null;
  logo?: string | null;
  site?: string | null;
  origem?: "tabela" | "site" | "canal" | string;
};

export type SlideTitulo = { tipo: "titulo"; kicker?: string | null; titulo: string; subtitulo?: string | null };
export type SlideDeclaracao = { tipo: "declaracao"; texto: string; autor?: string | null };
export type SlideGrade = { tipo: "grade"; titulo: string; itens: { titulo: string; texto: string }[] };
export type Coluna = { titulo: string; itens: string[] };
export type SlideComparacao = { tipo: "comparacao"; titulo: string; esquerda: Coluna; direita: Coluna };
export type SlideEtapas = { tipo: "etapas"; titulo: string; itens: { titulo: string; texto: string }[] };
export type Numero = { valor: number; sufixo?: string; rotulo: string; fonte: string };
export type SlideEstatisticas = { tipo: "estatisticas"; titulo: string; numeros: Numero[] };
export type No = { titulo: string; texto?: string | null };
export type SlideFluxo = { tipo: "fluxo"; titulo: string; nos: No[] };
export type SlideScreenshot = { tipo: "screenshot"; titulo: string; imagem?: string | null; legenda?: string | null };
export type SlideCta = { tipo: "cta"; titulo: string; texto?: string | null; url: string; imagem?: string | null };

export type Slide =
  | SlideTitulo
  | SlideDeclaracao
  | SlideGrade
  | SlideComparacao
  | SlideEtapas
  | SlideEstatisticas
  | SlideFluxo
  | SlideScreenshot
  | SlideCta;

export type Deck = {
  slug?: string;
  titulo: string;
  marca: Marca;
  slides: Slide[];
};

export const FPS = 30;
export const LARGURA = 1920;
export const ALTURA = 1080;
export const FRAMES_POR_SLIDE = 240;

// Deck mínimo para o Studio abrir sem --props (nunca renderizado pelo apresentacao.py).
export const DECK_EXEMPLO: Deck = {
  titulo: "Exemplo",
  marca: { nome: "CANAL", cor: "#22C55E", cor_2: null, logo: null, site: null, origem: "canal" },
  slides: [
    { tipo: "titulo", kicker: "Exemplo", titulo: "Slide de <b>exemplo</b> do Studio", subtitulo: "Abra com --props para ver um deck real" },
    { tipo: "cta", titulo: "Quer o método inteiro?", texto: "Tudo no Seu Site", url: "example.com", imagem: null },
  ],
};
