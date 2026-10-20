// Render de um deck pela API Node do Remotion (D-10):
//   node scripts/render.mjs <deck.json> <pasta saida> <pasta ativos>
// Um bundle para todos os slides; para cada slide-N: MP4 h264 (crf 18) e PNG do último frame.
// Progresso: uma linha `slide i/N ok` por slide. Qualquer erro: mensagem no stderr e código 1.
// Sem chave de licença (D-43): o enquadramento da licença é decisão do dono do canal, fora do código.
import { bundle } from "@remotion/bundler";
import { ensureBrowser, renderMedia, renderStill, selectComposition } from "@remotion/renderer";
import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const aqui = path.dirname(fileURLToPath(import.meta.url));
const raizDoMotion = path.resolve(aqui, "..");

const uso = () => {
  console.error("uso: node scripts/render.mjs <deck.json> <pasta saida> <pasta ativos>");
  process.exit(2);
};

const main = async () => {
  const [deckArq, saida, ativos] = process.argv.slice(2);
  if (!deckArq || !saida || !ativos) uso();
  const deck = JSON.parse(await readFile(deckArq, "utf-8"));
  if (!Array.isArray(deck.slides) || deck.slides.length === 0) {
    throw new Error("deck.json sem slides");
  }
  await mkdir(saida, { recursive: true });
  const inicio = Date.now();

  await ensureBrowser();
  const serveUrl = await bundle({
    entryPoint: path.join(raizDoMotion, "src", "index.ts"),
    publicDir: path.resolve(ativos),
    rootDir: raizDoMotion,
  });

  const total = deck.slides.length;
  for (let i = 1; i <= total; i++) {
    const nome = `slide-${String(i).padStart(2, "0")}`;
    const composition = await selectComposition({ serveUrl, id: `slide-${i}`, inputProps: deck });
    await renderMedia({
      composition,
      serveUrl,
      codec: "h264",
      crf: 18,
      inputProps: deck,
      outputLocation: path.join(saida, `${nome}.mp4`),
      overwrite: true,
    });
    await renderStill({
      composition,
      serveUrl,
      inputProps: deck,
      frame: composition.durationInFrames - 1,
      imageFormat: "png",
      output: path.join(saida, `${nome}.png`),
      overwrite: true,
    });
    console.log(`slide ${i}/${total} ok`);
  }
  console.log(`render concluido em ${Math.round((Date.now() - inicio) / 1000)} s`);
};

main().catch((erro) => {
  console.error(erro && erro.stack ? erro.stack : String(erro));
  process.exit(1);
});
