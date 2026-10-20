// Grafo das memórias da fábrica: cérebro (boas práticas de Instagram) e biblioteca (ideias de pauta)
// como uma rede neural em 3D. Núcleo -> base -> canal -> vídeo -> tema. Vídeo destilado acende e liga
// nos temas; vídeo bruto fica em nuvem apagada ao redor do canal. É vitrine: só lê /api/grafo.
import * as THREE from "./vendor/three.module.min.js";

const VERDE = new THREE.Color(0xef4444), VERDE2 = new THREE.Color(0xf87171), MENTA = new THREE.Color(0xfecaca), CLARO = new THREE.Color(0xf2f5f3), CINZA = new THREE.Color(0x8b9891);
const TAMANHO = { nucleo: 30, base: 24, canal: 13, tema: 10, video: 2.6 };
const PESO_DA_RELEVANCIA = { alta: 2.3, media: 1.8, baixa: 1.4, fora: 1.0 };

export function montar(palco, { dados, aoSelecionar, aoPassar }) {
  const nos = dados.nos.map((n, i) => ({ ...n, i, viz: [], elos: [], p: new THREE.Vector3(), v: new THREE.Vector3() }));
  const porId = new Map(nos.map((n) => [n.id, n]));
  const elos = dados.elos.map(([a, b], i) => ({ i, a: porId.get(a), b: porId.get(b) })).filter((e) => e.a && e.b);
  elos.forEach((e) => { e.a.viz.push(e.b); e.b.viz.push(e.a); e.a.elos.push(e); e.b.elos.push(e); e.forte = e.a.tipo !== "video" || e.b.tipo !== "video" ? (e.a.status === "destilado" || e.b.status === "destilado" || (e.a.tipo !== "video" && e.b.tipo !== "video")) : false; });
  const hubs = nos.filter((n) => n.tipo !== "video"), videos = nos.filter((n) => n.tipo === "video");

  // ponto de partida: cada base de um lado, o resto em nuvem perto de quem o segura
  const lado = { cerebro: -1, biblioteca: 1 }, acaso = (r) => new THREE.Vector3().randomDirection().multiplyScalar(r * Math.cbrt(Math.random()));
  for (const n of nos) {
    if (n.tipo === "nucleo") n.p.set(0, 0, 0);
    else if (n.tipo === "base") n.p.set(lado[n.base] * 50, 0, 0);
    else n.p.copy(acaso(n.tipo === "video" ? 40 : 30)).add(new THREE.Vector3(lado[n.base] * 50, 0, 0));
    n.mola = n.tipo === "video" ? (n.status === "destilado" ? 16 : 6 + Math.random() * 16) : 0;
  }

  const cena = new THREE.Scene(); cena.fog = new THREE.FogExp2(0x0d0f10, 0.0042);
  const render = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, alpha: true });
  render.setPixelRatio(Math.min(devicePixelRatio, 2)); render.setClearColor(0x000000, 0); render.domElement.className = "cena"; palco.prepend(render.domElement);
  const camera = new THREE.PerspectiveCamera(50, 1, 1, 900);

  // ---------- nós: um único Points com brilho desenhado no shader ----------
  const N = nos.length, pos = new Float32Array(N * 3), cor = new Float32Array(N * 3), tam = new Float32Array(N), forca = new Float32Array(N), fase = new Float32Array(N);
  function corDo(n) {
    if (n.tipo === "nucleo") return CLARO;
    if (n.tipo === "base") return n.base === "cerebro" ? VERDE : MENTA;
    if (n.tipo === "canal" || n.tipo === "tema") return n.base === "cerebro" ? VERDE2 : MENTA;
    if (n.status !== "destilado" || n.relevancia === "fora") return CINZA;
    return n.base === "cerebro" ? VERDE2 : CLARO;
  }
  nos.forEach((n) => { corDo(n).toArray(cor, n.i * 3); fase[n.i] = Math.random() * 6.28; forca[n.i] = 1;
    tam[n.i] = n.tipo === "video" ? TAMANHO.video * (PESO_DA_RELEVANCIA[n.relevancia] || 1) : TAMANHO[n.tipo] * (n.tipo === "tema" || n.tipo === "canal" ? 0.75 + Math.min(1.1, Math.log10(1 + (n.videos || 1)) * 0.42) : 1); });
  const geoNos = new THREE.BufferGeometry();
  geoNos.setAttribute("position", new THREE.BufferAttribute(pos, 3)); geoNos.setAttribute("cor", new THREE.BufferAttribute(cor, 3));
  geoNos.setAttribute("tam", new THREE.BufferAttribute(tam, 1)); geoNos.setAttribute("forca", new THREE.BufferAttribute(forca, 1)); geoNos.setAttribute("fase", new THREE.BufferAttribute(fase, 1));
  const matNos = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, uniforms: { tempo: { value: 0 }, escala: { value: 1 } },
    vertexShader: `attribute vec3 cor; attribute float tam; attribute float forca; attribute float fase; uniform float tempo; uniform float escala; varying vec3 vCor; varying float vForca; varying float vNevoa;
      void main() { vec4 mv = modelViewMatrix * vec4(position, 1.0); float pulso = 1.0 + 0.16 * sin(tempo * 1.7 + fase);
        gl_PointSize = tam * pulso * (0.55 + 0.75 * forca) * escala * 430.0 / -mv.z; gl_Position = projectionMatrix * mv; vCor = cor; vForca = forca; vNevoa = exp(-0.0026 * 0.0026 * mv.z * mv.z); }`,
    fragmentShader: `varying vec3 vCor; varying float vForca; varying float vNevoa;
      void main() { float d = length(gl_PointCoord - 0.5) * 2.0; if (d > 1.0) discard; float nucleo = smoothstep(0.22, 0.0, d); float halo = pow(1.0 - d, 3.2);
        vec3 c = mix(vCor, vec3(1.0), nucleo * 0.75); gl_FragColor = vec4(c, (nucleo + halo * 0.5) * min(vForca, 1.6) * vNevoa); }`,
  });
  cena.add(new THREE.Points(geoNos, matNos));

  // ---------- sinapses: linhas e os pulsos que correm por elas ----------
  const E = elos.length, posElo = new Float32Array(E * 6), corElo = new Float32Array(E * 6);
  const geoElos = new THREE.BufferGeometry(); geoElos.setAttribute("position", new THREE.BufferAttribute(posElo, 3)); geoElos.setAttribute("color", new THREE.BufferAttribute(corElo, 3));
  cena.add(new THREE.LineSegments(geoElos, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false })));
  const fortes = elos.filter((e) => e.forte), PULSOS = Math.min(520, Math.max(80, fortes.length));
  const pulsos = Array.from({ length: PULSOS }, () => ({ e: null, t: Math.random(), vel: 0, ida: true }));
  const posPulso = new Float32Array(PULSOS * 3), corPulso = new Float32Array(PULSOS * 3), tamPulso = new Float32Array(PULSOS).fill(1.7), forcaPulso = new Float32Array(PULSOS).fill(1), fasePulso = new Float32Array(PULSOS);
  const geoPulsos = new THREE.BufferGeometry(); geoPulsos.setAttribute("position", new THREE.BufferAttribute(posPulso, 3)); geoPulsos.setAttribute("cor", new THREE.BufferAttribute(corPulso, 3));
  geoPulsos.setAttribute("tam", new THREE.BufferAttribute(tamPulso, 1)); geoPulsos.setAttribute("forca", new THREE.BufferAttribute(forcaPulso, 1)); geoPulsos.setAttribute("fase", new THREE.BufferAttribute(fasePulso, 1));
  cena.add(new THREE.Points(geoPulsos, matNos));
  function novoPulso(p, de) {   // o pulso segue adiante pela rede: sai de onde o anterior chegou
    const opcoes = de ? de.elos.filter((e) => e.forte && visivel(e.a) && visivel(e.b)) : [];
    p.e = opcoes.length && Math.random() < 0.82 ? opcoes[(Math.random() * opcoes.length) | 0] : fortes[(Math.random() * fortes.length) | 0];
    p.ida = de ? p.e.a === de : Math.random() < 0.5; p.t = 0; p.vel = 0.35 + Math.random() * 0.75;
  }

  // poeira de fundo, para dar profundidade
  const poeira = new Float32Array(900 * 3); for (let i = 0; i < 900; i++) acaso(330).toArray(poeira, i * 3);
  const geoPoeira = new THREE.BufferGeometry(); geoPoeira.setAttribute("position", new THREE.BufferAttribute(poeira, 3));
  cena.add(new THREE.Points(geoPoeira, new THREE.PointsMaterial({ color: 0x4a3b3b, size: 0.9, transparent: true, opacity: 0.55, depthWrite: false })));

  // ---------- rótulos dos neurônios grandes ----------
  const rotulos = hubs.map((n) => { const el = document.createElement("button"); el.className = "rotulo-grafo " + n.tipo; el.textContent = n.tipo === "canal" ? n.nome.split(" - ")[0] : n.nome; el.onclick = () => seleciona(n); palco.append(el); return { n, el }; });

  // ---------- filtro, foco e destaque ----------
  let filtro = "tudo", foco = null, sobre = null, calor = 1;
  const visivel = (n) => n.tipo === "nucleo" || ((filtro === "tudo" || filtro === "destilados" || n.base === filtro) && (filtro !== "destilados" || n.tipo !== "video" || n.status === "destilado"));
  function pinta() {
    const alvo = foco || sobre, perto = alvo ? new Set([alvo, ...alvo.viz, ...(alvo.tipo === "base" || alvo.tipo === "nucleo" ? alvo.viz.flatMap((v) => v.viz) : [])]) : null;
    for (const n of nos) forca[n.i] = !visivel(n) ? 0 : !perto ? 1 : perto.has(n) ? (n === alvo ? 1.9 : 1.35) : 0.1;
    geoNos.attributes.forca.needsUpdate = true;
    for (const e of elos) {
      const on = visivel(e.a) && visivel(e.b), quente = perto && perto.has(e.a) && perto.has(e.b) && (e.a === alvo || e.b === alvo || alvo.tipo === "base" || alvo.tipo === "nucleo");
      const base = (e.a.base || e.b.base) === "cerebro" ? VERDE : MENTA, k = !on ? 0 : quente ? 1.0 : perto ? 0.02 : e.forte ? 0.34 : 0.075;
      for (let j = 0; j < 2; j++) { corElo[e.i * 6 + j * 3] = base.r * k; corElo[e.i * 6 + j * 3 + 1] = base.g * k; corElo[e.i * 6 + j * 3 + 2] = base.b * k; }
    }
    geoElos.attributes.color.needsUpdate = true;
  }
  function seleciona(n) { foco = n && foco !== n ? n : null; ajusta(); pinta(); aoSelecionar(foco && semVetores(foco)); enquadra(); }
  function enquadra() {   // a câmera mira o nó escolhido junto com os vizinhos, e recua o bastante para caberem
    if (!foco) { vista.alvoRaio = 185; return; }
    const grupo = [foco, ...foco.viz.filter((v) => forca[v.i] > 0)]; meio.set(0, 0, 0); grupo.forEach((g) => meio.add(g.p)); meio.multiplyScalar(1 / grupo.length);
    vista.alvoCentro.copy(meio).lerp(foco.p, 0.35); const alcance = Math.max(...grupo.map((g) => g.p.distanceTo(vista.alvoCentro)));
    vista.alvoRaio = Math.max(55, Math.min(300, alcance * 2.5 + 30));
  }
  const semVetores = (n) => ({ ...n, p: undefined, v: undefined, elos: undefined, viz: n.viz.filter((x) => x.tipo !== "video" || n.tipo !== "canal").slice(0, 40).map((x) => ({ id: x.id, tipo: x.tipo, nome: x.nome })), vizinhos: n.viz.length });

  // ---------- física: molas e repulsão, esfriando; a rede se organiza diante de quem olha ----------
  const d = new THREE.Vector3(), meio = new THREE.Vector3();
  function passo() {
    const k = calor;
    for (let i = 0; i < hubs.length; i++) for (let j = i + 1; j < hubs.length; j++) {   // neurônios grandes se afastam entre si
      const a = hubs[i], b = hubs[j]; d.subVectors(a.p, b.p); const r2 = Math.max(d.lengthSq(), 4), f = (a.tipo === "base" || b.tipo === "base" ? 1300 : 380) / r2; d.normalize().multiplyScalar(f * k); a.v.add(d); b.v.sub(d);
    }
    for (const n of videos) {
      for (let s = 0; s < 5; s++) { const o = videos[(Math.random() * videos.length) | 0]; if (o === n) continue; d.subVectors(n.p, o.p); const r2 = Math.max(d.lengthSq(), 1); if (r2 < 500) n.v.add(d.normalize().multiplyScalar(26 / r2 * k)); }
      for (const h of n.viz) if (h.tipo === "tema" || h.tipo === "canal") { d.subVectors(n.p, h.p); const r2 = Math.max(d.lengthSq(), 1); if (r2 < 60) n.v.add(d.normalize().multiplyScalar(30 / r2 * k)); }
    }
    for (const e of elos) {
      const alvo = e.a.tipo === "nucleo" ? 50 : e.a.tipo === "base" ? (e.b.tipo === "canal" ? 24 : 40) : (e.a.tipo === "video" ? e.a : e.b).mola, rigidez = e.a.tipo === "video" || e.b.tipo === "video" ? 0.035 : 0.09;
      d.subVectors(e.b.p, e.a.p); const dist = d.length() || 0.01, f = (dist - alvo) * rigidez * k; d.multiplyScalar(f / dist);
      const leve = (h) => Math.max(0.03, Math.min(0.5, 2 / (h.videos || 1)));   // tema com poucos vídeos vai até eles; tema grande fica onde está
      const pa = e.a.tipo === "video" ? 1 : e.b.tipo === "video" ? leve(e.a) : 0.5, pb = e.b.tipo === "video" ? 1 : e.a.tipo === "video" ? leve(e.b) : 0.5; e.a.v.addScaledVector(d, pa); e.b.v.addScaledVector(d, -pb);
    }
    for (const n of hubs) if (n.tipo === "canal" || n.tipo === "tema") {   // gravidade: tema e canal não fogem da própria memória
      const base = porId.get(n.base); d.subVectors(base.p, n.p); const dist = d.length(); if (dist > 38) n.v.addScaledVector(d, 0.05 * (dist - 38) / dist * k);
    }
    for (const n of nos) { if (n.tipo === "nucleo") { n.v.set(0, 0, 0); continue; } if (n.tipo === "base") { n.v.x += (lado[n.base] * 50 - n.p.x) * 0.08; n.v.y -= n.p.y * 0.08; n.v.z -= n.p.z * 0.08; } n.v.multiplyScalar(0.82); n.p.add(n.v); }
    calor = Math.max(0.02, calor * 0.992);
  }

  // ---------- câmera e ponteiro ----------
  const vista = { az: 0.25, el: 0.2, raio: 360, alvoRaio: 185, centro: new THREE.Vector3(), alvoCentro: new THREE.Vector3() };
  const calmo = matchMedia("(prefers-reduced-motion: reduce)").matches, el = render.domElement, tela = new THREE.Vector3();
  let arrasto = null, rodando = true, quadro = 0, ponteiro = null;
  function maisPerto(x, y) { let melhor = null, menor = 18 * 18; const r = el.getBoundingClientRect(), l = r.width, a = r.height;
    for (const n of nos) { if (!forca[n.i]) continue; tela.copy(n.p).project(camera); if (tela.z > 1) continue; const dx = (tela.x * 0.5 + 0.5) * l - x, dy = (-tela.y * 0.5 + 0.5) * a - y, alcance = n.tipo === "video" ? 1 : 0.35, q = (dx * dx + dy * dy) * alcance; if (q < menor) { menor = q; melhor = n; } }
    return melhor; }
  el.addEventListener("pointerdown", (ev) => { arrasto = { x: ev.clientX, y: ev.clientY, az: vista.az, el: vista.el, andou: 0 }; el.setPointerCapture(ev.pointerId); });
  el.addEventListener("pointermove", (ev) => { const r = el.getBoundingClientRect();
    if (arrasto) { arrasto.andou = Math.hypot(ev.clientX - arrasto.x, ev.clientY - arrasto.y); vista.az = arrasto.az - (ev.clientX - arrasto.x) * 0.005; vista.el = Math.max(-1.2, Math.min(1.2, arrasto.el + (ev.clientY - arrasto.y) * 0.004)); return; }
    ponteiro = { x: ev.clientX - r.left, y: ev.clientY - r.top }; });
  el.addEventListener("pointerleave", () => { ponteiro = null; if (sobre) { sobre = null; pinta(); aoPassar(null); } });
  el.addEventListener("pointerup", (ev) => { const clique = arrasto && arrasto.andou < 5; arrasto = null; if (clique) { const r = el.getBoundingClientRect(); seleciona(maisPerto(ev.clientX - r.left, ev.clientY - r.top)); } });
  el.addEventListener("wheel", (ev) => { ev.preventDefault(); vista.alvoRaio = Math.max(35, Math.min(420, vista.alvoRaio * (1 + ev.deltaY * 0.0012))); }, { passive: false });

  function ajusta() { const l = palco.clientWidth, a = palco.clientHeight; render.setSize(l, a, false); camera.aspect = l / a;
    if (foco && l > 900) camera.setViewOffset(l, a, 190, 0, l, a); else camera.clearViewOffset();   // a ficha abre à direita: a cena desliza para a esquerda
    camera.updateProjectionMatrix(); matNos.uniforms.escala.value = a / 800 * Math.min(devicePixelRatio, 2); }
  const observa = new ResizeObserver(ajusta); observa.observe(palco); ajusta(); pinta();
  pulsos.forEach((p) => { novoPulso(p, null); p.t = Math.random(); });

  const relogio = new THREE.Clock(); let conta = 0;
  function anima() {
    if (!rodando) return; quadro = requestAnimationFrame(anima);
    const dt = Math.min(relogio.getDelta(), 0.05), t = relogio.elapsedTime; conta++;
    if (calor > 0.021) { passo(); passo(); }
    for (const n of nos) { const o = n.i * 3, b = n.tipo === "video" ? 0.35 : 0.9;   // respiração: a rede nunca fica parada
      pos[o] = n.p.x + Math.sin(t * 0.5 + fase[n.i]) * b; pos[o + 1] = n.p.y + Math.cos(t * 0.43 + fase[n.i] * 1.3) * b; pos[o + 2] = n.p.z + Math.sin(t * 0.37 + fase[n.i] * 0.7) * b; }
    geoNos.attributes.position.needsUpdate = true;
    for (const e of elos) { const o = e.i * 6, a = e.a.i * 3, b = e.b.i * 3; posElo[o] = pos[a]; posElo[o + 1] = pos[a + 1]; posElo[o + 2] = pos[a + 2]; posElo[o + 3] = pos[b]; posElo[o + 4] = pos[b + 1]; posElo[o + 5] = pos[b + 2]; }
    geoElos.attributes.position.needsUpdate = true;
    pulsos.forEach((p, i) => { p.t += dt * p.vel; if (p.t >= 1 || !visivel(p.e.a) || !visivel(p.e.b)) novoPulso(p, p.ida ? p.e.b : p.e.a);
      const de = (p.ida ? p.e.a : p.e.b).i * 3, ate = (p.ida ? p.e.b : p.e.a).i * 3, k = p.t * p.t * (3 - 2 * p.t), o = i * 3;
      posPulso[o] = pos[de] + (pos[ate] - pos[de]) * k; posPulso[o + 1] = pos[de + 1] + (pos[ate + 1] - pos[de + 1]) * k; posPulso[o + 2] = pos[de + 2] + (pos[ate + 2] - pos[de + 2]) * k;
      const c = (p.e.a.base || p.e.b.base) === "cerebro" ? VERDE2 : CLARO; corPulso[o] = c.r; corPulso[o + 1] = c.g; corPulso[o + 2] = c.b;
      const alvo = foco || sobre; forcaPulso[i] = Math.sin(p.t * Math.PI) * (alvo && p.e.a !== alvo && p.e.b !== alvo ? 0.12 : 1); });
    geoPulsos.attributes.position.needsUpdate = geoPulsos.attributes.cor.needsUpdate = geoPulsos.attributes.forca.needsUpdate = true;
    matNos.uniforms.tempo.value = t;
    if (foco && calor > 0.021 && conta % 30 === 0) enquadra();
    if (!foco && conta % 20 === 0) { meio.set(0, 0, 0); let q = 0; for (const h of hubs) if (forca[h.i]) { meio.add(h.p); q++; } if (q) vista.alvoCentro.copy(meio.multiplyScalar(1 / q)); }   // a câmera mira o meio do que está aceso
    if (!arrasto && !calmo && !foco) vista.az += dt * 0.05;
    vista.raio += (vista.alvoRaio - vista.raio) * 0.04; vista.centro.lerp(vista.alvoCentro, 0.05);
    camera.position.set(vista.centro.x + Math.sin(vista.az) * Math.cos(vista.el) * vista.raio, vista.centro.y + Math.sin(vista.el) * vista.raio, vista.centro.z + Math.cos(vista.az) * Math.cos(vista.el) * vista.raio); camera.lookAt(vista.centro);
    if (ponteiro && !arrasto && conta % 3 === 0) { const n = maisPerto(ponteiro.x, ponteiro.y); if (n !== sobre) { sobre = n; el.style.cursor = n ? "pointer" : "grab"; if (!foco) pinta(); aoPassar(n ? { ...semVetores(n), x: ponteiro.x, y: ponteiro.y } : null); } }
    const l = palco.clientWidth, a = palco.clientHeight, alvo = foco || sobre;
    for (const r of rotulos) { tela.copy(r.n.p).project(camera); const some = tela.z > 1 || !forca[r.n.i] || (r.n.tipo === "tema" && vista.raio > 300 && r.n !== alvo);
      r.el.style.display = some ? "none" : ""; if (some) continue; const dist = camera.position.distanceTo(r.n.p);
      r.el.style.transform = `translate(-50%, 0) translate(${((tela.x * 0.5 + 0.5) * l).toFixed(1)}px, ${((-tela.y * 0.5 + 0.5) * a + 10 + tam[r.n.i] * 38 / dist).toFixed(1)}px)`;
      r.el.style.opacity = String(Math.max(0.12, Math.min(1, (alvo && forca[r.n.i] < 1 ? 0.18 : 1) * (1.35 - dist / 420)))); r.el.style.zIndex = String(1000 - Math.round(tela.z * 1000)); }
    render.render(cena, camera);
  }
  anima();
  const aoMudarVisibilidade = () => { if (document.hidden) { rodando = false; cancelAnimationFrame(quadro); } else if (!rodando) { rodando = true; relogio.getDelta(); anima(); } };
  document.addEventListener("visibilitychange", aoMudarVisibilidade);

  return {
    filtra(f) { filtro = f; if (foco && !visivel(foco)) seleciona(null); pinta(); },
    seleciona: (id) => seleciona(id ? porId.get(id) : null),
    reorganiza() { calor = 1; for (const n of videos) n.v.add(acaso(6)); },
    foto() { render.setClearColor(0x0d0f10, 1); render.render(cena, camera); const url = render.domElement.toDataURL("image/png"); render.setClearColor(0x000000, 0); return url; },
    desmontar() { rodando = false; cancelAnimationFrame(quadro); observa.disconnect(); document.removeEventListener("visibilitychange", aoMudarVisibilidade);
      cena.traverse((o) => { o.geometry?.dispose(); o.material?.dispose?.(); }); render.dispose(); render.domElement.remove(); rotulos.forEach((r) => r.el.remove()); },
  };
}
