// Escritório 3D da daily do canal: a equipe de agentes numa sala de agência, na identidade CANAL
// (cinza escuro, vermelho só em destaque). As falas vêm de /api/escritorio, que só lê o que a
// rotina já gravou. Clicar num boneco abre a ficha dele e a conversa, que passa pela daily.
import * as THREE from "./vendor/three.module.min.js";

const COR = { fundo: 0x121415, piso: 0x3a4044, parede: 0x2d3336, parede2: 0x272c2f, movel: 0x2b3033, tampo: 0x596268, metal: 0x0f1112,
  texto: 0xf2f5f3, verde: 0xef4444, verde2: 0xf87171, planta: 0x2f6b45, planta2: 0x3d8458, quente: 0xffe2b8 };
const PELE = [0xf1c9a5, 0xc68e63, 0x8d5a3b, 0xe8b792, 0x6f4329, 0xd9a577, 0xf5d3b5, 0xa86f48];
const VISUAL = {
  planejador: { roupa: 0xf2f5f3, cabelo: 0x1b1b1b, estilo: "curto", pele: 3, tela: "agenda", em_pe: true },
  analista: { roupa: 0x3a4145, cabelo: 0x3b2a20, estilo: "longo", pele: 0, oculos: true, tela: "grafico" },
  roteirista: { roupa: 0xd9ded9, cabelo: 0x8a4b2a, estilo: "coque", pele: 6, tela: "texto" },
  curador: { roupa: 0x5a6065, cabelo: 0x2a2320, estilo: "barba", pele: 2, tela: "videos" },
  bibliotecario: { roupa: 0xe8e2d4, cabelo: 0x4a3a2c, estilo: "longo", pele: 7, tela: "livros" },
  reviewer: { roupa: 0x2b3033, cabelo: 0x9aa19d, estilo: "curto", pele: 1, oculos: true, fone: true, tela: "checklist" },
  apresentador: { roupa: 0xc9d1cc, cabelo: 0x2b2118, estilo: "curto", pele: 4, tela: "slides", em_pe: true },
  validador: { roupa: 0x454c50, cabelo: 0x6b4a2b, estilo: "coque", pele: 5, oculos: true, tela: "relogio" },
};
const LUGAR = {   // x, z, giro do conjunto mesa + boneco
  analista: [-4.2, 2.7, 0.42], roteirista: [0.0, 3.0, 0.34], reviewer: [4.2, 3.3, 0.26],
  curador: [-2.4, -0.8, 0.4], bibliotecario: [2.2, -0.5, 0.32], planejador: [-0.6, -3.7, 0.55],
  apresentador: [4.6, -3.4, 0.5], validador: [-4.6, -3.4, 0.6],
};

const ESCALA = 1.28;   // boneco e mesa maiores que a sala: é diorama, não planta baixa
const ZB = -0.82;   // o boneco senta atrás da mesa, de frente para a câmera
const mat = (cor, extra = {}) => new THREE.MeshStandardMaterial({ color: cor, roughness: 0.78, metalness: 0.04, ...extra });
const brilho = (cor, forca = 1.6) => new THREE.MeshStandardMaterial({ color: cor, emissive: cor, emissiveIntensity: forca, roughness: 0.4 });
function peca(geo, material, x = 0, y = 0, z = 0, sombra = true) {
  const m = new THREE.Mesh(geo, material); m.position.set(x, y, z); m.castShadow = sombra; m.receiveShadow = true; return m;
}
const caixa = (l, a, p, material, x, y, z) => peca(new THREE.BoxGeometry(l, a, p), material, x, y, z);

// ---------- texturas desenhadas em canvas: telas, telão, piso ----------
function tela2d(l, a, desenha) {
  const c = document.createElement("canvas"); c.width = l; c.height = a;
  const g = c.getContext("2d"); g.fillStyle = "#0e1011"; g.fillRect(0, 0, l, a); desenha(g, l, a);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t;
}
const TELAS = {
  grafico(g, l, a) { g.fillStyle = "#EF4444"; [0.3, 0.5, 0.42, 0.7, 0.55, 0.85, 0.66].forEach((v, i) => g.fillRect(24 + i * 30, a - 24 - v * (a - 60), 20, v * (a - 60))); g.strokeStyle = "#F2F5F3"; g.lineWidth = 3; g.beginPath(); g.moveTo(20, a - 50); g.lineTo(90, a - 90); g.lineTo(150, a - 70); g.lineTo(236, a - 130); g.stroke(); },
  agenda(g, l, a) { for (let i = 0; i < 5; i++) for (let j = 0; j < 4; j++) { g.fillStyle = (i + j) % 4 === 0 ? "#EF4444" : "#2B3033"; g.fillRect(16 + i * 46, 18 + j * 36, 40, 30); } },
  texto(g, l, a) { g.fillStyle = "#EF4444"; g.fillRect(18, 18, 120, 12); g.fillStyle = "#A8B0AC"; [200, 170, 214, 150, 190, 120, 205].forEach((w, i) => g.fillRect(18, 44 + i * 17, w, 7)); },
  checklist(g, l, a) { for (let i = 0; i < 6; i++) { g.strokeStyle = "#A8B0AC"; g.lineWidth = 2; g.strokeRect(18, 16 + i * 25, 14, 14); if (i < 4) { g.fillStyle = "#EF4444"; g.fillRect(21, 19 + i * 25, 8, 8); } g.fillStyle = "#A8B0AC"; g.fillRect(44, 20 + i * 25, 120 + (i * 37) % 70, 7); } },
  slides(g, l, a) { for (let i = 0; i < 3; i++) { g.fillStyle = i === 1 ? "#F2F5F3" : "#232729"; g.fillRect(14 + i * 80, 30, 70, 88); g.fillStyle = "#EF4444"; g.fillRect(22 + i * 80, 40, 40, 8); g.fillStyle = i === 1 ? "#16181A" : "#A8B0AC"; g.fillRect(22 + i * 80, 56, 52, 5); g.fillRect(22 + i * 80, 66, 44, 5); } g.fillStyle = "#2B3033"; g.fillRect(14, 132, 230, 10); },
  relogio(g, l, a) { g.strokeStyle = "#EF4444"; g.lineWidth = 6; g.beginPath(); g.arc(70, a / 2, 44, 0, Math.PI * 2); g.stroke(); g.strokeStyle = "#F2F5F3"; g.lineWidth = 4; g.beginPath(); g.moveTo(70, a / 2); g.lineTo(70, a / 2 - 30); g.moveTo(70, a / 2); g.lineTo(92, a / 2 + 8); g.stroke(); g.fillStyle = "#A8B0AC"; [0, 1, 2, 3].forEach((i) => g.fillRect(136, 34 + i * 26, 100, 10)); g.fillStyle = "#EF4444"; g.fillRect(136, 34, 60, 10); },
  videos(g, l, a) { for (let i = 0; i < 2; i++) for (let j = 0; j < 2; j++) { const x = 16 + i * 118, y = 16 + j * 70; g.fillStyle = "#232729"; g.fillRect(x, y, 106, 58); g.fillStyle = "#EF4444"; g.beginPath(); g.moveTo(x + 44, y + 17); g.lineTo(x + 44, y + 41); g.lineTo(x + 66, y + 29); g.fill(); } },
  livros(g, l, a) { [["#EF4444", 60], ["#F2F5F3", 84], ["#A8B0AC", 70], ["#F87171", 96], ["#2B3033", 76], ["#F2F5F3", 64], ["#EF4444", 90]].forEach(([c, h], i) => { g.fillStyle = c; g.fillRect(20 + i * 32, a - 24 - h, 24, h); }); g.fillStyle = "#A8B0AC"; g.fillRect(12, a - 24, 236, 5); },
};
function texturaDoTelao(dados) {
  return tela2d(1024, 512, (g, l, a) => {
    const fonte = (px, peso = 700) => `${peso} ${px}px "Chakra Petch", system-ui, sans-serif`;
    g.fillStyle = "#EF4444"; g.font = fonte(30, 600); g.textBaseline = "top";
    g.fillText("DAILY DO CANAL  ·  " + dados.data.slice(8, 10) + "/" + dados.data.slice(5, 7), 48, 40);
    g.fillStyle = "#F2F5F3"; g.font = fonte(64); g.fillText(dados.handle || "@seu-canal", 48, 84);
    const n = (v) => v == null ? "–" : Number(v).toLocaleString("pt-BR", { maximumFractionDigits: 2 });
    const k = dados.kpis || {};
    [["VIEWS 7D", n(k.views), "#F2F5F3"], ["INSCRITOS GANHOS", k.inscritos_ganhos == null ? "–" : "+" + n(k.inscritos_ganhos), "#EF4444"], ["ENGAJAMENTO", n(k.taxa_engajamento) + "%", "#F2F5F3"]].forEach(([r, v, cor], i) => {
      g.fillStyle = "#A8B0AC"; g.font = `600 20px "JetBrains Mono", monospace`; g.fillText(r, 48 + i * 320, 196);
      g.fillStyle = cor; g.font = `600 56px "JetBrains Mono", monospace`; g.fillText(v, 48 + i * 320, 226);
    });
    const s = dados.serie_views || [], max = Math.max(1, ...s.map((d) => d.valor || 0)), larg = (l - 96) / Math.max(1, s.length);
    s.forEach((d, i) => { const h = (d.valor || 0) / max * 150; g.fillStyle = "#EF4444"; g.fillRect(48 + i * larg, a - 40 - h, larg - 8, h); });
  });
}
function texturaDoPiso() {
  const t = tela2d(512, 512, (g, l) => {
    g.fillStyle = "#8a9298"; g.fillRect(0, 0, l, l);
    for (let i = 0; i < 8; i++) { g.fillStyle = i % 2 ? "#a3abb0" : "#969ea4"; g.fillRect(0, i * 64, l, 61); }
    g.fillStyle = "rgba(0,0,0,0.10)"; for (let i = 0; i < 8; i++) g.fillRect((i * 173) % 512, i * 64, 2, 62);
  });
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(4, 3); return t;
}
function texturaDaJanela() {
  return tela2d(256, 512, (g, l, a) => {
    const grad = g.createLinearGradient(0, 0, 0, a); grad.addColorStop(0, "#0c1512"); grad.addColorStop(0.6, "#12261d"); grad.addColorStop(1, "#1a3a2a");
    g.fillStyle = grad; g.fillRect(0, 0, l, a);
    for (let p = 0; p < 7; p++) { const x = p * 38, h = 120 + ((p * 97) % 190); g.fillStyle = "#0a0f0d"; g.fillRect(x, a - h, 34, h);
      for (let j = 0; j < h / 18; j++) for (let i = 0; i < 3; i++) if ((p * 7 + j * 3 + i) % 4 === 0) { g.fillStyle = (j + i) % 5 ? "#ffe2b8" : "#F87171"; g.fillRect(x + 5 + i * 9, a - h + 8 + j * 18, 5, 8); } }
  });
}

// ---------- mobília ----------
function sala(cena, dados) {
  const piso = peca(new THREE.BoxGeometry(16, 0.4, 11.5), mat(COR.piso, { map: texturaDoPiso(), roughness: 0.72 }), 0, -0.2, 0.25, false);
  cena.add(piso);
  cena.add(caixa(16, 5.2, 0.35, mat(COR.parede), 0, 2.6, -5.5), caixa(0.35, 5.2, 11.5, mat(COR.parede2), -8, 2.6, 0.25));
  // fita de LED no rodapé e no alto: o verde da marca como linha, não como superfície
  cena.add(peca(new THREE.BoxGeometry(15.6, 0.05, 0.05), brilho(COR.verde, 2.2), 0.1, 0.12, -5.3, false), peca(new THREE.BoxGeometry(0.05, 0.05, 11.2), brilho(COR.verde, 2.2), -7.8, 0.12, 0.3, false),
    peca(new THREE.BoxGeometry(15.6, 0.04, 0.04), brilho(COR.verde2, 1.2), 0.1, 4.9, -5.3, false));
  // telão da daily, com as KPIs reais
  const telao = new THREE.Group();
  telao.add(caixa(6.3, 3.25, 0.14, mat(COR.metal, { roughness: 0.4 }), 0, 0, 0));
  telao.add(peca(new THREE.PlaneGeometry(6.0, 3.0), new THREE.MeshBasicMaterial({ map: texturaDoTelao(dados), toneMapped: false }), 0, 0, 0.08, false));
  telao.position.set(2.0, 2.9, -5.25); cena.add(telao);
  // janelas com a cidade à noite
  const janela = texturaDaJanela();
  [-2.6, 0.4, 3.4].forEach((z) => { cena.add(caixa(0.1, 3.3, 2.3, mat(COR.metal), -7.8, 2.7, z));
    const vidro = peca(new THREE.PlaneGeometry(2.1, 3.1), new THREE.MeshBasicMaterial({ map: janela, toneMapped: false }), -7.73, 2.7, z, false); vidro.rotation.y = Math.PI / 2; cena.add(vidro); });
  // quadro de pautas
  const quadro = new THREE.Group(); quadro.add(caixa(2.6, 1.7, 0.08, mat(0xe9ece9, { roughness: 0.5 }), 0, 0, 0));
  [[-0.9, 0.45, COR.verde], [-0.3, 0.5, 0xf2f5f3], [0.35, 0.42, 0xa8b0ac], [0.95, 0.5, COR.verde2], [-0.85, -0.2, 0xa8b0ac], [-0.2, -0.15, COR.verde], [0.45, -0.22, 0xf2f5f3], [-0.5, -0.6, 0xa8b0ac]].forEach(([x, y, c]) =>
    quadro.add(caixa(0.42, 0.36, 0.02, mat(c, { roughness: 0.95 }), x, y, 0.05)));
  quadro.position.set(-5.2, 2.9, -5.25); cena.add(quadro);
  // letreiro
  const letreiro = peca(new THREE.PlaneGeometry(2.6, 0.7), new THREE.MeshBasicMaterial({ transparent: true, toneMapped: false, map: tela2d(512, 138, (g, l, a) => { g.clearRect(0, 0, l, a); g.fillStyle = "#EF4444"; g.font = `700 110px "Chakra Petch", system-ui, sans-serif`; g.textBaseline = "middle"; g.fillText("CANAL", 8, a / 2 + 6); }) }), 6.7, 4.35, -5.3, false);
  letreiro.material.map.premultiplyAlpha = false; letreiro.material.blending = THREE.AdditiveBlending; cena.add(letreiro);
  // tapete, plantas, estante, luminárias
  const tapete = peca(new THREE.CylinderGeometry(2.0, 2.0, 0.04, 48), mat(0x2f4a3b, { roughness: 1 }), -1.3, 0.02, -3.6, false); cena.add(tapete);
  [[5.4, -4.5, 1.25], [-7.0, 5.0, 1.1], [7.2, 5.0, 0.9]].forEach(([x, z, e]) => cena.add(planta(x, z, e)));
  cena.add(estante(7.3, -3.2));
  [[-3.3, 1.6], [3.3, 2.0], [0.4, -1.6], [-5.2, -2.6]].forEach(([x, z]) => cena.add(luminaria(x, z)));
  cena.add(sofa(7.1, 0.4));
}
function planta(x, z, escala) {
  const g = new THREE.Group(); g.add(peca(new THREE.CylinderGeometry(0.34, 0.26, 0.6, 20), mat(0xe9ece9, { roughness: 0.6 }), 0, 0.3, 0));
  [[0, 1.15, 0, 0.55], [0.3, 0.95, 0.15, 0.4], [-0.28, 1.0, -0.1, 0.42], [0.05, 1.55, -0.05, 0.38], [-0.1, 0.85, 0.3, 0.33]].forEach(([a, b, c, r], i) =>
    g.add(peca(new THREE.IcosahedronGeometry(r, 1), mat(i % 2 ? COR.planta2 : COR.planta, { flatShading: true }), a, b, c)));
  g.position.set(x, 0, z); g.scale.setScalar(escala); g.userData.balanca = true; return g;
}
function estante(x, z) {
  const g = new THREE.Group(); g.add(caixa(0.5, 3.0, 2.6, mat(COR.movel), 0, 1.5, 0));
  for (let n = 0; n < 4; n++) { g.add(caixa(0.46, 0.05, 2.5, mat(COR.tampo), -0.04, 0.35 + n * 0.72, 0));
    for (let i = 0; i < 7; i++) { const h = 0.34 + ((i * 3 + n) % 4) * 0.06; g.add(caixa(0.3, h, 0.14, mat([0xe9ece9, 0x3a4145, COR.verde, 0xa8b0ac, 0x16181a][(i + n * 2) % 5]), -0.12, 0.38 + n * 0.72 + h / 2, -1.05 + i * 0.2)); } }
  g.position.set(x, 0, z); return g;
}
function luminaria(x, z) {
  const g = new THREE.Group(); g.add(peca(new THREE.CylinderGeometry(0.012, 0.012, 1.6, 6), mat(COR.metal), 0, 4.4, 0, false));
  g.add(peca(new THREE.ConeGeometry(0.42, 0.36, 24, 1, true), mat(COR.metal, { side: THREE.DoubleSide, roughness: 0.35 }), 0, 3.55, 0, false));
  g.add(peca(new THREE.SphereGeometry(0.12, 16, 12), brilho(COR.quente, 3), 0, 3.46, 0, false));
  const luz = new THREE.PointLight(0xfff0dc, 24, 11, 1.6); luz.position.set(0, 3.3, 0); g.add(luz); g.position.set(x, 0, z); return g;
}
function sofa(x, z) {
  const g = new THREE.Group(), tecido = mat(0x343a3e, { roughness: 1 });
  g.add(caixa(1.0, 0.42, 2.3, tecido, 0, 0.36, 0), caixa(0.3, 0.9, 2.3, tecido, 0.42, 0.6, 0), caixa(1.0, 0.62, 0.26, tecido, 0, 0.46, 1.14), caixa(1.0, 0.62, 0.26, tecido, 0, 0.46, -1.14));
  g.add(caixa(0.5, 0.34, 0.5, mat(COR.verde, { roughness: 0.95 }), -0.05, 0.72, -0.6)); g.children.at(-1).rotation.set(0.2, 0.4, 0.15);
  g.position.set(x, 0, z); return g;
}
function mesa(tipoDeTela) {
  const g = new THREE.Group();
  g.add(caixa(2.1, 0.08, 1.0, mat(COR.tampo, { roughness: 0.55 }), 0, 1.0, 0));
  [[-0.95, -0.4], [0.95, -0.4], [-0.95, 0.4], [0.95, 0.4]].forEach(([x, z]) => g.add(caixa(0.06, 1.0, 0.06, mat(COR.metal), x, 0.5, z)));
  g.add(peca(new THREE.BoxGeometry(2.0, 0.03, 0.03), brilho(COR.verde, 1.6), 0, 0.93, 0.49, false));
  // notebook: a tampa fica de costas para a câmera, com o ponto verde aceso
  const note = new THREE.Group(); note.add(caixa(0.62, 0.03, 0.42, mat(0x3a4145, { metalness: 0.5, roughness: 0.35 }), 0, 0, 0));
  const tampa = new THREE.Group(); tampa.add(caixa(0.62, 0.42, 0.025, mat(0x3a4145, { metalness: 0.5, roughness: 0.35 }), 0, 0.21, 0));
  tampa.add(peca(new THREE.PlaneGeometry(0.56, 0.36), brilho(0xcfeedd, 0.9), 0, 0.21, -0.014, false)); tampa.children.at(-1).rotation.y = Math.PI;
  tampa.add(peca(new THREE.CircleGeometry(0.035, 20), brilho(COR.verde, 2.5), 0, 0.23, 0.014, false));
  tampa.position.set(0, 0.015, 0.2); tampa.rotation.x = 0.28; note.add(tampa); note.position.set(0.1, 1.06, 0.05); g.add(note);
  // monitor lateral virado para a câmera, com a tela do ofício de cada um
  const monitor = new THREE.Group(); monitor.add(caixa(0.95, 0.6, 0.04, mat(COR.metal, { roughness: 0.35 }), 0, 0.5, 0));
  monitor.add(peca(new THREE.PlaneGeometry(0.88, 0.53), new THREE.MeshBasicMaterial({ map: tela2d(264, 160, TELAS[tipoDeTela]), toneMapped: false }), 0, 0.5, 0.024, false));
  monitor.add(caixa(0.06, 0.3, 0.04, mat(COR.metal), 0, 0.12, -0.03), caixa(0.32, 0.02, 0.2, mat(COR.metal), 0, 0.0, -0.03));
  monitor.position.set(-0.68, 1.05, -0.2); monitor.rotation.y = 0.75; g.add(monitor);
  // caneca
  g.add(peca(new THREE.CylinderGeometry(0.06, 0.05, 0.13, 16), mat(0xf2f5f3, { roughness: 0.4 }), 0.78, 1.11, 0.25));
  const luzDaTela = new THREE.PointLight(0xcfeedd, 1.6, 2.2, 2); luzDaTela.position.set(0.1, 1.45, -0.25); g.add(luzDaTela);
  return g;
}
function cadeira() {
  const g = new THREE.Group(), m = mat(COR.metal, { roughness: 0.6 });
  g.add(caixa(0.62, 0.1, 0.6, m, 0, 0.62, 0), caixa(0.6, 0.75, 0.09, m, 0, 1.08, -0.3), peca(new THREE.CylinderGeometry(0.04, 0.04, 0.5, 10), m, 0, 0.32, 0));
  for (let i = 0; i < 5; i++) { const p = caixa(0.36, 0.04, 0.06, m, 0, 0.07, 0); p.geometry.translate(0.18, 0, 0); p.rotation.y = i * Math.PI * 0.4; g.add(p); }
  return g;
}

// ---------- os bonecos ----------
function boneco(v) {
  const g = new THREE.Group(), pele = mat(PELE[v.pele], { roughness: 0.62 }), roupa = mat(v.roupa, { roughness: 0.9 }), calca = mat(0x16181a, { roughness: 0.9 });
  const tronco = new THREE.Group(); g.add(tronco);
  tronco.add(peca(new THREE.CapsuleGeometry(0.3, 0.42, 8, 20), roupa, 0, 0, 0));
  const cracha = peca(new THREE.BoxGeometry(0.1, 0.13, 0.02), brilho(COR.verde, 0.9), 0.12, 0.02, 0.295); tronco.add(cracha);
  const cabeca = new THREE.Group(); cabeca.position.y = 0.72; tronco.add(cabeca);
  cabeca.add(peca(new THREE.SphereGeometry(0.36, 32, 24), pele));
  const olhos = [-0.125, 0.125].map((x) => { const o = peca(new THREE.SphereGeometry(0.043, 14, 12), mat(0x141414, { roughness: 0.2 }), x, 0.02, 0.325, false);
    o.add(peca(new THREE.SphereGeometry(0.014, 8, 8), new THREE.MeshBasicMaterial({ color: 0xffffff }), 0.014, 0.016, 0.034, false)); cabeca.add(o); return o; });
  const boca = peca(new THREE.TorusGeometry(0.07, 0.014, 8, 20, Math.PI), mat(0x5a2a22, { roughness: 0.5 }), 0, -0.11, 0.325, false); boca.rotation.z = Math.PI; cabeca.add(boca);
  [-0.22, 0.22].forEach((x) => { const b = peca(new THREE.SphereGeometry(0.06, 12, 10), new THREE.MeshBasicMaterial({ color: 0xff8f8f, transparent: true, opacity: 0.28 }), x, -0.07, 0.275, false); b.scale.set(1, 0.6, 0.4); cabeca.add(b); });
  const fio = mat(v.cabelo, { roughness: 0.95 });
  const calota = (raio, ate, inclina) => { const c = peca(new THREE.SphereGeometry(raio, 28, 18, 0, Math.PI * 2, 0, Math.PI * ate), fio); c.rotation.x = inclina; return c; };
  if (v.estilo === "curto") cabeca.add(calota(0.385, 0.5, -0.32));
  if (v.estilo === "coque") { cabeca.add(calota(0.385, 0.52, -0.3), peca(new THREE.SphereGeometry(0.16, 16, 12), fio, 0, 0.4, -0.12)); }
  if (v.estilo === "longo") { cabeca.add(calota(0.39, 0.55, -0.34)); const atras = peca(new THREE.CapsuleGeometry(0.3, 0.42, 6, 16), fio, 0, -0.22, -0.16); atras.scale.set(1.05, 1, 0.55); cabeca.add(atras); }
  if (v.estilo === "cacheado") [[0, 0.3, 0], [0.22, 0.22, 0.05], [-0.22, 0.22, 0.05], [0.13, 0.3, -0.18], [-0.13, 0.3, -0.18], [0.3, 0.08, -0.1], [-0.3, 0.08, -0.1], [0, 0.18, -0.28], [0.1, 0.33, 0.14], [-0.1, 0.33, 0.14]].forEach(([x, y, z]) => cabeca.add(peca(new THREE.SphereGeometry(0.15, 12, 10), fio, x, y, z)));
  if (v.estilo === "barba") { cabeca.add(calota(0.383, 0.42, -0.4)); const barba = peca(new THREE.SphereGeometry(0.375, 28, 18, 0, Math.PI * 2, Math.PI * 0.56, Math.PI * 0.44), fio, 0, 0, 0.025); cabeca.add(barba); boca.position.z = 0.39; }
  if (v.estilo === "bone") { cabeca.add(calota(0.39, 0.46, -0.2)); const aba = peca(new THREE.CylinderGeometry(0.27, 0.27, 0.03, 24, 1, false, -Math.PI / 2, Math.PI), fio, 0, 0.14, 0.26); cabeca.add(aba); }
  if (v.oculos) { const aro = mat(0x101010, { roughness: 0.3 }); [-0.125, 0.125].forEach((x) => cabeca.add(peca(new THREE.TorusGeometry(0.085, 0.013, 8, 24), aro, x, 0.02, 0.335, false))); cabeca.add(caixa(0.08, 0.014, 0.014, aro, 0, 0.03, 0.34)); }
  if (v.fone) { const arco = peca(new THREE.TorusGeometry(0.4, 0.028, 8, 28, Math.PI), mat(COR.metal), 0, 0.02, 0, false); cabeca.add(arco);
    [-0.4, 0.4].forEach((x) => { const c = peca(new THREE.CylinderGeometry(0.1, 0.1, 0.08, 18), brilho(COR.verde, 0.8), x, 0, 0); c.rotation.z = Math.PI / 2; cabeca.add(c); }); }
  const bracos = [-1, 1].map((lado) => { const ombro = new THREE.Group(); ombro.position.set(lado * 0.33, 0.22, 0.02);
    const b = peca(new THREE.CapsuleGeometry(0.085, 0.36, 6, 12), roupa, 0, -0.22, 0); ombro.add(b); ombro.add(peca(new THREE.SphereGeometry(0.095, 14, 12), pele, 0, -0.47, 0)); tronco.add(ombro); return ombro; });
  if (v.em_pe) {
    tronco.position.y = 1.2; [-0.14, 0.14].forEach((x) => g.add(peca(new THREE.CapsuleGeometry(0.115, 0.55, 6, 12), calca, x, 0.5, 0), caixa(0.2, 0.1, 0.34, mat(0xf2f5f3), x, 0.06, 0.05)));
    bracos[0].rotation.set(-0.15, 0, -0.12); bracos[1].rotation.set(-0.9, 0, 0.5);
    const tablet = caixa(0.34, 0.24, 0.02, brilho(0xcfeedd, 0.7), 0, -0.5, 0.12); bracos[1].add(tablet);
  } else {
    tronco.position.y = 1.12; [-0.15, 0.15].forEach((x) => { const coxa = peca(new THREE.CapsuleGeometry(0.115, 0.34, 6, 12), calca, x, 0.78, 0.3); coxa.rotation.x = Math.PI / 2; g.add(coxa); g.add(peca(new THREE.CapsuleGeometry(0.1, 0.38, 6, 12), calca, x, 0.42, 0.56), caixa(0.19, 0.1, 0.32, mat(0xf2f5f3), x, 0.07, 0.62)); });
    bracos.forEach((b, i) => b.rotation.set(-1.05, 0, (i ? 1 : -1) * 0.18));
  }
  g.userData.partes = { tronco, cabeca, olhos, bracos, boca }; return g;
}

// ---------- montagem ----------
export function montar(palco, { dados, aoSelecionar }) {
  const cena = new THREE.Scene(); cena.background = new THREE.Color(COR.fundo); cena.fog = new THREE.Fog(COR.fundo, 30, 52);
  const render = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  render.setPixelRatio(Math.min(devicePixelRatio, 2)); render.shadowMap.enabled = true; render.shadowMap.type = THREE.PCFSoftShadowMap;
  render.toneMapping = THREE.ACESFilmicToneMapping; render.toneMappingExposure = 1.5; render.outputColorSpace = THREE.SRGBColorSpace;
  render.domElement.className = "cena"; palco.prepend(render.domElement);
  const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 120);
  cena.add(new THREE.HemisphereLight(0xeaf3ee, 0x2b3033, 1.9));
  const sol = new THREE.DirectionalLight(0xfff1dc, 3.2); sol.position.set(9, 14, 10); sol.castShadow = true; sol.shadow.mapSize.set(2048, 2048);
  Object.assign(sol.shadow.camera, { left: -12, right: 12, top: 10, bottom: -10, near: 1, far: 40 }); sol.shadow.bias = -0.0004; sol.shadow.radius = 5; cena.add(sol);
  const verdeDoTelao = new THREE.PointLight(COR.verde, 30, 10, 1.6); verdeDoTelao.position.set(2.2, 2.6, -3.9); cena.add(verdeDoTelao);
  sala(cena, dados);

  const equipe = {}, clicaveis = [];
  for (const agente of dados.equipe) {
    const v = VISUAL[agente.id], [x, z, giro] = LUGAR[agente.id] || [0, 0, 0]; if (!v) continue;
    const posto = new THREE.Group(); posto.position.set(x, 0, z); posto.rotation.y = giro; posto.scale.setScalar(ESCALA);
    const b = boneco(v); posto.add(b);
    if (v.em_pe) b.position.set(0, 0, 0); else { b.position.set(0, 0, ZB); posto.add(cadeira().translateZ(ZB - 0.06), mesa(v.tela)); }
    const anel = peca(new THREE.RingGeometry(0.62, 0.72, 48), new THREE.MeshBasicMaterial({ color: COR.verde2, transparent: true, opacity: 0, toneMapped: false }), 0, 0.03, v.em_pe ? 0 : ZB, false);
    anel.rotation.x = -Math.PI / 2; posto.add(anel);
    const alvo = peca(new THREE.CylinderGeometry(0.62, 0.62, 2.3, 12), new THREE.MeshBasicMaterial({ visible: false }), 0, 1.15, v.em_pe ? 0 : ZB, false); alvo.userData.id = agente.id; posto.add(alvo); clicaveis.push(alvo);
    cena.add(posto);
    const cracha = document.createElement("button"); cracha.className = "cracha"; cracha.textContent = agente.nome; cracha.onclick = () => seleciona(agente.id); palco.append(cracha);
    const balao = document.createElement("div"); balao.className = "balao"; balao.hidden = true; balao.onclick = () => seleciona(agente.id); palco.append(balao);
    equipe[agente.id] = { ...agente, v, posto, b, anel, cracha, balao, fase: Math.random() * 6, falando: 0, pisca: 2 + Math.random() * 4, olha: 0 };
  }

  // câmera: diorama visto de três quartos, com balanço leve; arrastar gira, a roda aproxima
  const RAIO = 23.5, CENTRO = [0.2, 1.5, -0.4];
  const vista = { azimute: 0.5, alvoAz: 0.5, elev: 0.4, raio: RAIO, alvoRaio: RAIO, centro: new THREE.Vector3(...CENTRO), alvoCentro: new THREE.Vector3(...CENTRO) };
  const calmo = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let arrasto = null, selecionado = null, sobre = null, rodando = true, quadro = 0;
  const raio = new THREE.Raycaster(), ponteiro = new THREE.Vector2();
  function acha(ev) { const r = render.domElement.getBoundingClientRect(); ponteiro.set((ev.clientX - r.left) / r.width * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1); raio.setFromCamera(ponteiro, camera); return raio.intersectObjects(clicaveis)[0]?.object.userData.id || null; }
  const el = render.domElement;
  el.addEventListener("pointerdown", (ev) => { arrasto = { x: ev.clientX, az: vista.alvoAz, andou: 0 }; el.setPointerCapture(ev.pointerId); });
  el.addEventListener("pointermove", (ev) => { if (arrasto) { arrasto.andou = Math.abs(ev.clientX - arrasto.x); vista.alvoAz = Math.max(0.05, Math.min(1.15, arrasto.az - (ev.clientX - arrasto.x) * 0.004)); } else { sobre = acha(ev); el.style.cursor = sobre ? "pointer" : "grab"; } });
  el.addEventListener("pointerup", (ev) => { const clique = arrasto && arrasto.andou < 5; arrasto = null; if (clique) seleciona(acha(ev)); });
  el.addEventListener("wheel", (ev) => { ev.preventDefault(); vista.alvoRaio = Math.max(12, Math.min(30, vista.alvoRaio + ev.deltaY * 0.012)); }, { passive: false });

  function seleciona(id, avisa = true) {
    selecionado = id && equipe[id] ? id : null;
    if (selecionado) { const p = equipe[selecionado].posto.position; vista.alvoCentro.set(p.x * 0.6, 1.5, p.z * 0.6 - 0.2); vista.alvoRaio = Math.min(vista.alvoRaio, 19.5); }
    else { vista.alvoCentro.set(...CENTRO); vista.alvoRaio = RAIO; }
    ajusta(); if (avisa) aoSelecionar(selecionado);
  }

  // a daily em voz alta: uma fala por vez, no ritmo de leitura
  let indice = -1, proxima = 1.2, falaAtual = null; const fixos = {};
  function fala(agora) {
    if (agora < proxima || !dados.falas.length) return;
    if (falaAtual) equipe[falaAtual.quem].balao.classList.remove("visivel");
    indice = (indice + 1) % dados.falas.length; falaAtual = dados.falas[indice];
    const a = equipe[falaAtual.quem]; if (!a) { falaAtual = null; return; }
    if (!fixos[a.id]) { a.balao.textContent = falaAtual.texto; a.balao.hidden = false; requestAnimationFrame(() => a.balao.classList.add("visivel")); }
    a.falando = 1; proxima = agora + Math.max(3.4, falaAtual.texto.length * 0.062) + (indice === dados.falas.length - 1 ? 2.5 : 0.5);
  }
  function fixaBalao(id, texto, classe = "") {   // resposta ao Usuário, ou "pensando": tem prioridade sobre a daily
    const a = equipe[id]; if (!a) return;
    if (texto == null) { delete fixos[id]; a.balao.classList.remove("visivel", "pensando", "resposta"); return; }
    fixos[id] = true; a.balao.textContent = texto; a.balao.hidden = false; a.balao.className = "balao visivel " + classe; a.falando = 1;
  }

  const v3 = new THREE.Vector3(), relogio = new THREE.Clock();
  function ancora(objeto, altura, elemento, acima, sobe = 0) {
    objeto.getWorldPosition(v3); v3.y += altura; v3.project(camera);
    const x = (v3.x * 0.5 + 0.5) * palco.clientWidth, y = (-v3.y * 0.5 + 0.5) * palco.clientHeight;
    elemento.style.transform = `translate(-50%, ${acima ? "-100%" : "0"}) translate(${x.toFixed(1)}px, ${(y - sobe).toFixed(1)}px)`;
    elemento.style.zIndex = String(1000 - Math.round(v3.z * 1000) + (acima ? 50 : 0));
  }
  function ajusta() {
    const l = palco.clientWidth, a = palco.clientHeight; render.setSize(l, a, false); camera.aspect = l / a; camera.fov = l / a < 1.2 ? 40 : 30;
    // o chat ocupa a direita do palco: a cena desliza para a esquerda e ninguém fica atrás dele
    if (l > 1000) camera.setViewOffset(l, a, 195, 0, l, a); else camera.clearViewOffset();
    camera.updateProjectionMatrix();
  }
  const observa = new ResizeObserver(ajusta); observa.observe(palco); ajusta();

  function anima() {
    if (!rodando) return; quadro = requestAnimationFrame(anima);
    const dt = Math.min(relogio.getDelta(), 0.05), t = relogio.elapsedTime;
    fala(t);
    vista.azimute += (vista.alvoAz + (calmo || arrasto ? 0 : Math.sin(t * 0.18) * 0.05) - vista.azimute) * 0.06; vista.raio += (vista.alvoRaio - vista.raio) * 0.06; vista.centro.lerp(vista.alvoCentro, 0.06);
    camera.position.set(vista.centro.x + Math.sin(vista.azimute) * Math.cos(vista.elev) * vista.raio, vista.centro.y + Math.sin(vista.elev) * vista.raio, vista.centro.z + Math.cos(vista.azimute) * Math.cos(vista.elev) * vista.raio);
    camera.lookAt(vista.centro);
    const quemFala = falaAtual && equipe[falaAtual.quem];
    for (const a of Object.values(equipe)) {
      const p = a.b.userData.partes, f = t + a.fase; a.falando = Math.max(0, a.falando - dt * 0.22);
      const ativo = quemFala === a || fixos[a.id];
      p.tronco.position.y = (a.v.em_pe ? 1.2 : 1.12) + Math.sin(f * 1.6) * 0.012 + (ativo ? Math.abs(Math.sin(t * 5.5)) * 0.035 : 0);
      p.cabeca.rotation.x = Math.sin(f * 0.7) * 0.05 + (ativo ? Math.sin(t * 6) * 0.06 : 0.06); p.cabeca.rotation.z = Math.sin(f * 0.43) * 0.04;
      let alvoY = Math.sin(f * 0.31) * 0.2;   // quem não fala olha de vez em quando para quem está falando
      if (quemFala && quemFala !== a) { const d = quemFala.posto.position.clone().sub(a.posto.position); alvoY = THREE.MathUtils.clamp(Math.atan2(d.x, d.z) - a.posto.rotation.y, -0.7, 0.7) * 0.45; }
      else if (ativo) alvoY = THREE.MathUtils.clamp(vista.azimute - a.posto.rotation.y, -0.6, 0.6);
      a.olha += (alvoY - a.olha) * 0.05; p.cabeca.rotation.y = a.olha;
      p.boca.scale.y = ativo ? 1 + Math.abs(Math.sin(t * 11)) * 0.9 : 1;
      if (!a.v.em_pe && !ativo) p.bracos.forEach((b, i) => { b.rotation.x = -1.05 + Math.sin(f * 9 + i * 1.7) * 0.05; }); else if (a.v.em_pe) p.bracos[0].rotation.x = -0.15 + (ativo ? Math.sin(t * 3) * 0.35 - 0.4 : Math.sin(f) * 0.05);
      a.pisca -= dt; const fechado = a.pisca < 0.12; if (a.pisca < 0) a.pisca = 2.5 + Math.random() * 4; p.olhos.forEach((o) => { o.scale.y = fechado ? 0.12 : 1; });
      const destaque = a.id === selecionado ? 0.95 : a.id === sobre ? 0.55 : 0; a.anel.material.opacity += (destaque - a.anel.material.opacity) * 0.15; a.anel.rotation.z = t * 0.6;
      const topo = (a.v.em_pe ? 2.42 : 2.3) * ESCALA; ancora(a.b, topo, a.cracha, true, 0); ancora(a.b, topo, a.balao, true, 30);
      a.cracha.classList.toggle("ativo", a.id === selecionado || a.id === sobre);
    }
    cena.traverse((o) => { if (o.userData.balanca) o.rotation.z = Math.sin(t * 0.6 + o.position.x) * 0.012; });
    render.render(cena, camera);
  }
  anima();
  const aoMudarVisibilidade = () => { if (document.hidden) { rodando = false; cancelAnimationFrame(quadro); } else if (!rodando) { rodando = true; relogio.getDelta(); anima(); } };
  document.addEventListener("visibilitychange", aoMudarVisibilidade);

  return {
    seleciona, fixaBalao, foca: (id) => seleciona(id, false),
    foto() { render.render(cena, camera); return render.domElement.toDataURL("image/png"); },
    desmontar() {
      rodando = false; cancelAnimationFrame(quadro); observa.disconnect(); document.removeEventListener("visibilitychange", aoMudarVisibilidade);
      cena.traverse((o) => { o.geometry?.dispose(); [].concat(o.material || []).forEach((m) => { m.map?.dispose(); m.dispose(); }); });
      render.dispose(); render.domElement.remove(); Object.values(equipe).forEach((a) => { a.balao.remove(); a.cracha.remove(); });
    },
  };
}
