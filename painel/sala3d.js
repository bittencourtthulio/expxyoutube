// Escritório 3D (a equipe na sala, falando a daily tirada dos relatórios) e grafo 3D do cérebro e da biblioteca.
// As cenas vêm de escritorio.js e grafo.js (módulos three.js carregados sob demanda). O chat do escritório usa as
// mesmas conversas por agente da Reunião: sem agente escolhido, fala com "Todos".
const sala3d = { api: null, dados: null, para: null, conversa: null, digitando: false, falou: null, soltar: null, relogio: null, visto: 0 };
const nomeDoAgente = (id) => sala3d.dados?.equipe.find((a) => a.id === id)?.nome || nomeDe(id);
const dataLonga = (iso) => new Date(iso + "T12:00:00").toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" });
const canalDoEscritorio = () => sala3d.para || "todos";

async function abreEscritorio(el) {
  el.innerHTML = `<div class="palco" id="palco"><div class="titulo"><b>A daily de hoje</b><span id="palco-data">carregando a sala</span></div>
    <div class="comandos"><button class="botao leve" data-palco="cheia">Tela cheia</button><button class="botao leve" data-palco="foto">Foto da cena</button><small>arraste para girar · role para aproximar · clique em alguém para falar só com ele</small></div>
    <aside class="ficha chat" id="chat"></aside></div>`;
  try {
    await carregaEquipe();
    const [modulo, dados] = await Promise.all([import("/estatico/escritorio.js"), pega("/api/escritorio"), document.fonts.ready]);
    if (estado.aba !== "escritorio") return;
    sala3d.dados = dados;
    await atualizaChatDoEscritorio(true);
    sala3d.api = modulo.montar(document.getElementById("palco"), { dados, aoSelecionar: (id) => escolheAgente(id) });
    document.getElementById("palco-data").textContent = dataLonga(dados.data) + " · " + dados.falas.length + " falas, todas tiradas dos relatórios";
    clearInterval(sala3d.relogio);
    sala3d.relogio = setInterval(() => { if (estado.aba === "escritorio") atualizaChatDoEscritorio(); }, 1800);
  } catch (erro) { el.querySelector(".titulo span").textContent = "não consegui montar a sala 3D: " + erro.message; }
}
function fechaEscritorio() {
  sala3d.api?.desmontar(); sala3d.api = null; clearInterval(sala3d.relogio); clearTimeout(sala3d.soltar);
}
async function escolheAgente(id) {
  sala3d.para = id || null; sala3d.conversa = null; sala3d.visto = 0;
  sala3d.api?.foca(sala3d.para);
  await atualizaChatDoEscritorio(true);
  document.getElementById("chat-texto")?.focus();
}
async function atualizaChatDoEscritorio(primeira = false) {
  const canal = (estado.canais || []).find((c) => c.id === canalDoEscritorio()); if (!canal) return;
  let r;
  try { r = await pega("/api/chat?sessao=" + encodeURIComponent(canal.sessao)); } catch { return; }
  const antes = sala3d.visto, mudou = !sala3d.conversa || r.mensagens.length !== antes || r.digitando !== sala3d.digitando;
  sala3d.conversa = r; sala3d.digitando = r.digitando; sala3d.visto = r.mensagens.length;
  const ultima = r.mensagens.at(-1);
  if (!primeira && sala3d.api && ultima && r.mensagens.length > antes && ultima.autor !== "usuario" && !ultima.erro) {   // quem respondeu fala também na sala
    const curto = ultima.texto.length > 240 ? ultima.texto.slice(0, 238).replace(/\s+\S*$/, "") + "..." : ultima.texto;
    if (sala3d.falou && sala3d.falou !== ultima.autor) sala3d.api.fixaBalao(sala3d.falou, null);
    sala3d.falou = ultima.autor; sala3d.api.foca(ultima.autor); sala3d.api.fixaBalao(ultima.autor, curto, "resposta");
    clearTimeout(sala3d.soltar); sala3d.soltar = setTimeout(() => sala3d.api?.fixaBalao(ultima.autor, null), Math.min(30000, 9000 + curto.length * 70));
  }
  if (sala3d.api && r.digitando && sala3d.para) sala3d.api.fixaBalao(sala3d.para, "digitando", "pensando");
  if (mudou || primeira) desenhaChatDoEscritorio();
}
function desenhaChatDoEscritorio() {
  const chat = document.getElementById("chat"); if (!chat) return;
  const rascunho = chat.querySelector("#chat-texto")?.value ?? "", tinhaFoco = document.activeElement?.id === "chat-texto";
  const falaDoDia = sala3d.para && sala3d.dados?.falas.find((f) => f.quem === sala3d.para)?.texto;
  const mensagens = sala3d.conversa?.mensagens || [];
  chat.innerHTML = `<header><div><h2>Chat com a equipe</h2><p>${sala3d.para ? `falando com <b style="color:var(--marca-2)">${esc(nomeDoAgente(sala3d.para))}</b>` : "responde quem for dono do assunto"}</p></div></header>
    <div class="linha-campos" style="margin:0 0 8px"><select id="chat-para" aria-label="Para quem"><option value="">Toda a equipe</option>${(sala3d.dados?.equipe || []).map((a) => `<option value="${esc(a.id)}" ${a.id === sala3d.para ? "selected" : ""}>${esc(a.nome)}</option>`).join("")}</select></div>
    <div class="rolagem" id="chat-rolagem">${falaDoDia ? `<p class="msg rotina"><span class="autor">${esc(nomeDoAgente(sala3d.para))} · na daily de hoje</span>${esc(falaDoDia)}</p>` : ""}
      ${mensagens.length ? "" : `<p class="vazio" style="font-size:13px">Pergunte sobre o canal ou peça uma ação. A conversa é a mesma da aba Reunião.</p>`}
      ${mensagens.slice(-30).map((m) => m.autor === "usuario"
        ? `<div class="meu"><p class="msg">${esc(m.texto)}</p><p class="levar">deixar para a rotina: <button data-levar="tarefa" data-texto="${esc(m.texto)}">tarefa</button> · <button data-levar="nao-fazer" data-texto="${esc(m.texto)}">não fazer mais</button> · <button data-levar="aprendizado" data-texto="${esc(m.texto)}">aprendizado</button></p></div>`
        : `<p class="msg rotina ${m.erro ? "falha" : ""}"><span class="autor">${esc(m.erro ? "painel" : nomeDoAgente(m.autor))} · ${esc(m.quando.slice(11, 16))}</span>${esc(m.texto)}</p>`).join("")}
      ${sala3d.digitando ? `<p class="pensando">${esc(sala3d.para ? nomeDoAgente(sala3d.para) : "a equipe")} está digitando</p>` : ""}</div>
    <textarea id="chat-texto" placeholder="Escreva para a equipe. Enter envia." ${sala3d.digitando ? "disabled" : ""}></textarea>
    <button class="botao" data-palco="enviar-chat" ${sala3d.digitando ? "disabled" : ""}>Enviar</button><p class="erro-carga" id="erro-3d"></p>`;
  const campo = chat.querySelector("#chat-texto"); campo.value = rascunho; if (tinhaFoco && !sala3d.digitando) campo.focus();
  const rolagem = chat.querySelector("#chat-rolagem"); rolagem.scrollTop = rolagem.scrollHeight;
}
async function enviaChatDoEscritorio() {
  const campo = document.getElementById("chat-texto"), texto = campo.value.trim(); if (!texto || sala3d.digitando) return;
  campo.value = ""; sala3d.digitando = true; desenhaChatDoEscritorio();
  try {
    await manda("/api/chat", { canal: canalDoEscritorio(), texto });
    if (sala3d.para) sala3d.api?.fixaBalao(sala3d.para, "digitando", "pensando");
    await atualizaChatDoEscritorio();
  } catch (erro) {
    sala3d.digitando = false; desenhaChatDoEscritorio();
    document.getElementById("chat-texto").value = texto; document.getElementById("erro-3d").textContent = erro.message;
  }
}

// ---------- grafo do cérebro e da biblioteca ----------
const rede = { api: null, dados: null };
const NOME_DO_TIPO = { nucleo: "núcleo", base: "memória", canal: "canal", tema: "tema", video: "vídeo" };
async function abreGrafo(el) {
  el.innerHTML = `<div class="palco rede" id="palco"><div class="titulo"><b>A rede de memórias</b><span id="palco-data">ligando os neurônios</span></div>
    <div class="contagem" id="contagem"></div>
    <div class="filtros-grafo">${[["tudo", "Tudo"], ["cerebro", "Cérebro"], ["biblioteca", "Biblioteca"], ["destilados", "Só destilados"]].map(([k, n]) => `<button data-filtro-grafo="${k}" aria-pressed="${k === "tudo"}">${n}</button>`).join("")}</div>
    <div class="dica-grafo" id="dica-grafo" hidden></div>
    <div class="comandos"><button class="botao leve" data-palco="cheia">Tela cheia</button><button class="botao leve" data-palco="foto-grafo">Foto</button><button class="botao leve" data-palco="reorganizar">Reorganizar</button><small>arraste para girar · role para aproximar · clique num ponto para seguir as ligações</small></div>
    <div class="legenda"><span style="color:#F87171"><i></i>cérebro destilado</span><span style="color:#F2F5F3"><i></i>biblioteca destilada</span><span style="color:#7c8581"><i></i>bruto, esperando destilação</span></div></div>`;
  try {
    const [modulo, dados] = await Promise.all([import("/estatico/grafo.js"), pega("/api/grafo"), document.fonts.ready]);
    if (estado.aba !== "grafo") return;
    rede.dados = dados;
    const v = dados.nos.filter((n) => n.tipo === "video"), conta = (f) => dados.nos.filter(f).length;
    document.getElementById("contagem").innerHTML = [[v.length, "vídeos"], [v.filter((x) => x.status === "destilado").length, "destilados"], [conta((n) => n.tipo === "canal"), "canais"], [conta((n) => n.tipo === "tema"), "temas"], [dados.elos.length, "sinapses"]].map(([n, r]) => `<div><b>${esc(num(n))}</b><span>${r}</span></div>`).join("");
    document.getElementById("palco-data").textContent = "cérebro e biblioteca, nota por nota, como estão no disco agora";
    rede.api = modulo.montar(document.getElementById("palco"), { dados, aoSelecionar: desenhaFichaDoNo, aoPassar: desenhaDicaDoNo });
  } catch (erro) { el.querySelector(".titulo span").textContent = "não consegui montar o grafo: " + erro.message; }
}
function fechaGrafo() { rede.api?.desmontar(); rede.api = null; }
function desenhaDicaDoNo(n) {
  const dica = document.getElementById("dica-grafo"); if (!dica) return;
  if (!n) { dica.hidden = true; return; }
  const extra = n.tipo === "video" ? [n.canal, n.data && dataCurta(n.data), n.status === "destilado" ? "relevância " + (n.relevancia || "–") : "bruto"].filter(Boolean).join(" · ")
    : `${NOME_DO_TIPO[n.tipo]} · ${num(n.videos ?? n.vizinhos)} ${n.tipo === "nucleo" ? "memórias" : "vídeos"}`;
  dica.innerHTML = `<b>${esc(n.nome)}</b><span>${esc(extra)}</span>`; dica.hidden = false;
  const palco = document.getElementById("palco");
  dica.style.transform = `translate(${Math.min(n.x + 16, palco.clientWidth - 320)}px, ${Math.min(n.y + 16, palco.clientHeight - 90)}px)`;
}
function desenhaFichaDoNo(n) {
  const palco = document.getElementById("palco"); if (!palco) return; palco.querySelector(".ficha")?.remove(); if (!n) return;
  const nomeDoTema = (id) => rede.dados.nos.find((x) => x.id === `${n.base}:tema:${id}`)?.nome || id;
  const corpo = n.tipo === "video"
    ? `<p class="rotulo">${esc(n.canal || "")} · ${esc(n.data ? dataCurta(n.data) + " " + n.data.slice(0, 4) : "")}</p>
       <p>${n.status === "destilado" ? etiqueta("destilado", "marca") + " " + etiqueta("relevância " + (n.relevancia || "–"), n.relevancia === "fora" ? "" : "frio") : etiqueta("bruto", "") + ` <small style="color:var(--tinta-3)">ainda não virou ${n.base === "cerebro" ? "boa prática" : "ideia de pauta"}</small>`}</p>
       ${n.views != null ? `<p style="color:var(--tinta-2);font-size:13px">${esc(num(n.views))} visualizações no YouTube na ingestão</p>` : ""}
       ${n.temas?.length ? `<p class="rotulo" style="margin-top:12px">Temas</p><div class="temas">${n.temas.map((t) => `<button class="etiqueta marca" data-no="${esc(n.base + ":tema:" + t)}">${esc(nomeDoTema(t))}</button>`).join("")}</div>` : ""}
       ${/^https:\/\/(www\.)?youtube\.com\//.test(n.url || "") ? `<p style="margin-top:12px"><a href="${esc(n.url)}" target="_blank" rel="noopener noreferrer">Abrir o vídeo</a></p>` : ""}`
    : `<p style="color:var(--tinta-2)">${esc(n.cobre || n.papel || "")}</p><div class="numeros" style="margin-top:12px"><div><b>${esc(num(n.videos ?? n.vizinhos))}</b><span>${n.tipo === "nucleo" ? "memórias" : "vídeos"}</span></div>${n.destilados != null ? `<div><b>${esc(num(n.destilados))}</b><span>destilados</span></div>` : ""}</div>
       ${n.viz?.length ? `<p class="rotulo">Ligado a</p><div class="temas">${n.viz.map((x) => `<button class="etiqueta ${x.tipo === "video" ? "" : "marca"}" data-no="${esc(x.id)}" style="white-space:normal;text-align:left;text-transform:none;letter-spacing:0;line-height:1.3">${esc(x.nome)}</button>`).join("")}</div>${n.vizinhos > n.viz.length ? `<p class="vazio" style="font-size:12px">e mais ${esc(num(n.vizinhos - n.viz.length))}</p>` : ""}` : ""}`;
  palco.insertAdjacentHTML("beforeend", `<aside class="ficha"><header><div><p class="rotulo" style="margin:0 0 6px">${esc(NOME_DO_TIPO[n.tipo])}${n.base ? " · " + esc(n.base === "cerebro" ? "cérebro" : "biblioteca") : ""}</p><h2 style="font-size:${n.tipo === "video" ? 17 : 22}px;line-height:1.25">${esc(n.nome)}</h2></div><button class="botao leve" data-palco="fechar-no">Fechar</button></header><div class="rolagem">${corpo}</div></aside>`);
}

// ---------- eventos das duas cenas ----------
document.addEventListener("change", (e) => { if (e.target.id === "chat-para") escolheAgente(e.target.value); });
document.addEventListener("keydown", (e) => {
  if (e.target.id === "chat-texto" && e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); enviaChatDoEscritorio(); }
});
document.addEventListener("click", async (e) => {
  if (!["escritorio", "grafo"].includes(estado.aba)) return;
  const b = e.target.closest("button"); if (!b) return; const d = b.dataset;
  if (d.no) return rede.api?.seleciona(d.no);
  if (d.filtroGrafo) { rede.api?.filtra(d.filtroGrafo); document.querySelectorAll("[data-filtro-grafo]").forEach((x) => x.setAttribute("aria-pressed", x === b)); return; }
  if (d.levar) {   // registro opcional na daily; pedido direto já pode ser executado no chat
    try { await manda("/api/novo", { tipo: d.levar, texto: d.texto, para: sala3d.para || "ambos" }); b.parentElement.textContent = "registrado na daily como " + TIPOS_DAILY[d.levar].toLowerCase(); }
    catch (erro) { document.getElementById("erro-3d").textContent = erro.message; }
    return;
  }
  if (!d.palco) return;
  const palco = document.getElementById("palco");
  if (d.palco === "cheia") return document.fullscreenElement ? document.exitFullscreen() : palco.requestFullscreen();
  if (d.palco === "foto-grafo") { const a = document.createElement("a"); a.href = rede.api.foto(); a.download = "rede-de-memorias-canal.png"; a.click(); return; }
  if (d.palco === "reorganizar") return rede.api?.reorganiza();
  if (d.palco === "fechar-no") return rede.api?.seleciona(null);
  if (d.palco === "foto") { const a = document.createElement("a"); a.href = sala3d.api.foto(); a.download = `escritorio-canal-${sala3d.dados.data}.png`; a.click(); return; }
  if (d.palco === "enviar-chat") return enviaChatDoEscritorio();
});
