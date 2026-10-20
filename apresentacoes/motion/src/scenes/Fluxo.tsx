// Diagrama de fluxo (3 a 6 nós): os nós entram em sequência e as setas se desenham entre eles; com 5 ou
// 6 nós o fluxo dobra em duas linhas e a seta de retorno desce até a linha de baixo. Depois que tudo
// entrou, um nó por vez ganha o brilho da marca (um brilho por frame, regra do tema), como quem aponta
// no quadro. Serve para aula: pipeline, arquitetura, ciclo, caminho do dado.
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { Entrance } from "../components/Entrance";
import { CenaProps, Moldura, slideDe, TituloDeSecao, useMedidas } from "./Slide";

const INICIO = 24;      // frame em que o primeiro nó entra
const POR_NO = 9;       // defasagem entre nós (regra 3: nada entra junto)
const SETA_ATRASO = 5;  // a seta sai depois do nó de origem assentar

type Caixa = { x: number; y: number; w: number; h: number; linha: number };

const caixas = (n: number, inner: number, u: number): { itens: Caixa[]; alturaTotal: number } => {
  const linhas = n <= 4 ? 1 : 2;
  const colunas = linhas === 1 ? n : Math.ceil(n / 2);
  const gapX = 96 * u;
  const gapY = 120 * u;
  const w = (inner - gapX * (colunas - 1)) / colunas;
  const h = (linhas === 1 ? 230 : 200) * u;
  const itens: Caixa[] = [];
  for (let i = 0; i < n; i++) {
    const linha = Math.floor(i / colunas);
    const coluna = i % colunas;
    itens.push({ x: coluna * (w + gapX), y: linha * (h + gapY), w, h, linha });
  }
  return { itens, alturaTotal: linhas * h + (linhas - 1) * gapY };
};

/** Caminho da seta entre dois nós e o comprimento dele (para o traço se desenhar). */
const seta = (a: Caixa, b: Caixa, u: number): { d: string; len: number } => {
  const folga = 14 * u;
  if (a.linha === b.linha) {
    const x1 = a.x + a.w + folga, x2 = b.x - folga, y = a.y + a.h / 2;
    return { d: `M ${x1} ${y} L ${x2} ${y}`, len: Math.max(1, x2 - x1) };
  }
  // retorno: sai pela direita do último nó da linha, desce até o meio do vão e volta para o primeiro da linha de baixo
  const x1 = a.x + a.w + folga, y1 = a.y + a.h / 2;
  const xDir = x1 + 34 * u;
  const yMeio = a.y + a.h + (b.y - (a.y + a.h)) / 2;
  const xEsq = b.x - 34 * u - folga;
  const x2 = b.x - folga, y2 = b.y + b.h / 2;
  const d = `M ${x1} ${y1} L ${xDir} ${y1} L ${xDir} ${yMeio} L ${xEsq} ${yMeio} L ${xEsq} ${y2} L ${x2} ${y2}`;
  const len = (xDir - x1) + (yMeio - y1) + (xDir - xEsq) + (y2 - yMeio) + (x2 - xEsq);
  return { d, len };
};

export const Fluxo: React.FC<CenaProps> = ({ deck, index }) => {
  const s = slideDe(deck, index, "fluxo");
  const { u, inner } = useMedidas();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const n = s.nos.length;
  const { itens, alturaTotal } = caixas(n, inner, u);
  const fim = INICIO + n * POR_NO + 30;
  // depois que tudo entrou, o brilho anda de nó em nó (um por vez), como o dedo do professor no quadro
  const ativo = frame >= fim ? Math.floor((frame - fim) / (fps * 1.2)) % n : -1;
  const cor = theme.colors.accent;

  return (
    <Moldura deck={deck} index={index}>
      <TituloDeSecao texto={s.titulo} />
      <div style={{ position: "relative", width: inner, height: alturaTotal }}>
        <svg width={inner} height={alturaTotal} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
          <defs>
            <marker id="ponta" markerWidth="12" markerHeight="12" refX="9" refY="6" orient="auto" markerUnits="userSpaceOnUse">
              <path d="M 1 1 L 10 6 L 1 11 z" fill={cor} />
            </marker>
          </defs>
          {itens.slice(0, -1).map((a, i) => {
            const b = itens[i + 1];
            const { d, len } = seta(a, b, u);
            const p = spring({ frame: frame - (INICIO + (i + 1) * POR_NO + SETA_ATRASO), fps, config: theme.spring.smooth });
            const desenhado = interpolate(p, [0, 1], [len, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            const brilhando = ativo === i || ativo === i + 1;
            return (
              <path
                key={i}
                d={d}
                fill="none"
                stroke={brilhando ? cor : theme.colors.textSoft}
                strokeWidth={brilhando ? 4 * u : 3 * u}
                strokeLinejoin="round"
                strokeDasharray={len}
                strokeDashoffset={desenhado}
                markerEnd={p > 0.97 ? "url(#ponta)" : undefined}
                opacity={brilhando ? 1 : 0.7}
              />
            );
          })}
        </svg>
        {s.nos.map((no, i) => {
          const c = itens[i];
          const brilha = ativo === i;
          return (
            <div key={i} style={{ position: "absolute", left: c.x, top: c.y, width: c.w, height: c.h }}>
              <Entrance delay={INICIO + i * POR_NO} variant={i % 2 === 0 ? "rise" : "fall"} style={{ height: "100%" }}>
                <div
                  style={{
                    boxSizing: "border-box",
                    height: "100%",
                    padding: `${22 * u}px ${26 * u}px`,
                    borderRadius: 18 * u,
                    background: theme.colors.surface,
                    border: `2px solid ${brilha ? cor : theme.colors.line}`,
                    boxShadow: brilha ? `0 0 0 1px ${cor}33, 0 0 40px ${cor}55` : "none",
                    display: "flex",
                    flexDirection: "column",
                    gap: 10 * u,
                  }}
                >
                  <span style={{ fontFamily: theme.fonts.mono, fontSize: 20 * u, color: cor, letterSpacing: 2 }}>
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <h3 style={{ margin: 0, fontFamily: theme.fonts.displayAlt, fontWeight: 700, fontSize: 32 * u, lineHeight: 1.1 }}>{no.titulo}</h3>
                  {no.texto ? (
                    <p style={{ margin: 0, fontFamily: theme.fonts.body, fontSize: 23 * u, lineHeight: 1.3, color: theme.colors.textSoft }}>{no.texto}</p>
                  ) : null}
                </div>
              </Entrance>
            </div>
          );
        })}
      </div>
    </Moldura>
  );
};
