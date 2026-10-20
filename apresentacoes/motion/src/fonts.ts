// Fontes da identidade CANAL via @remotion/google-fonts (D-12: a tipografia não muda com a marca).
// Nunca confie na fonte do sistema para o título: o Chromium cai para uma serifada sem avisar.
import { loadFont as loadAnton } from "@remotion/google-fonts/Anton";
import { loadFont as loadChakraPetch } from "@remotion/google-fonts/ChakraPetch";
import { loadFont as loadJetBrainsMono } from "@remotion/google-fonts/JetBrainsMono";

const anton = loadAnton();
const chakraPetch = loadChakraPetch("normal", { weights: ["400", "500", "600", "700"] });
const jetBrainsMono = loadJetBrainsMono("normal", { weights: ["400", "500"] });

export const loadedFonts = {
  display: anton.fontFamily,
  displayAlt: chakraPetch.fontFamily,
  body: chakraPetch.fontFamily,
  mono: jetBrainsMono.fontFamily,
};

export const waitForFonts = () =>
  Promise.all([anton.waitUntilDone(), chakraPetch.waitUntilDone(), jetBrainsMono.waitUntilDone()]);
