// Sala de reunião: uma conversa persistente por agente (e "Todos"), com os fios da daily do mesmo agente na linha do tempo.
const reuniao = { canal: "todos", conversas: {}, rascunhos: {}, enviando: false, erro: "" };
const fiosDoCanal = (canal) => (estado.daily?.itens || []).filter((f) => canal === "todos" ? ["todos", "ambos"].includes(f.para) : f.para === canal);

async function abreReuniao(el) {
  await Promise.all([carregaEquipe(), carregaDaily()]);
  const r = await pega("/api/chat/canais"); estado.canais = r.canais;
  el.innerHTML = `<section class="reuniao"><aside class="reuniao-nav" id="reuniao-nav" aria-label="Canais da reunião"></aside>
    <section class="conversa"><header class="conversa-cabeca" id="conversa-cabeca"></header>
    <div class="conversa-historico" id="conversa-historico" role="log" aria-live="polite"></div>
    <form class="conversa-compor" id="conversa-form"><label class="rotulo" for="reuniao-texto">Sua mensagem</label>
      <textarea id="reuniao-texto" rows="2" placeholder="Escreva sua mensagem…"></textarea>
      <div class="compor-rodape"><small>Enter envia · Shift + Enter quebra a linha · o pedido pode ser executado na hora</small><button class="botao" id="reuniao-enviar" type="submit">Enviar ↑</button></div>
      <p class="erro-carga" id="erro-reuniao" role="alert"></p></form></section></section>`;
  desenhaNavReuniao();
  await atualizaConversa();
}

function desenhaNavReuniao() {
  const nav = document.getElementById("reuniao-nav"); if (!nav) return;
  const aguarda = (id) => (estado.canais || []).find((c) => c.id === id)?.aguarda_usuario || fiosDoCanal(id).some((f) => f.aguarda_usuario);
  const botao = (id, nome, papel) => `<button class="canal-botao" data-canal="${esc(id)}" aria-current="${reuniao.canal === id}" title="${esc(papel)}">
    <span class="avatar-equipe">${esc(nome.slice(0, 2))}</span><span><b>${esc(nome)}</b><small>${esc(papel)}</small></span>${aguarda(id) ? '<span class="espera" aria-label="aguardando sua resposta">?</span>' : ""}</button>`;
  nav.innerHTML = `<p class="rotulo">Sala de reunião</p>${botao("todos", "Todos", "A equipe reunida")}
    <h2>Equipe <span>${(estado.equipe || []).length}</span></h2>${(estado.equipe || []).map((a) => botao(a.id, a.nome, a.papel)).join("")}
    <p class="nav-ajuda">Cada agente guarda a própria conversa. Os fios da daily enviados a ele aparecem junto.</p>`;
}

async function atualizaConversa() {
  const c = (estado.canais || []).find((x) => x.id === reuniao.canal); if (!c) return;
  reuniao.conversas[reuniao.canal] = await pega("/api/chat?sessao=" + encodeURIComponent(c.sessao));
  desenhaConversa();
}

function desenhaConversa() {
  const hist = document.getElementById("conversa-historico"); if (!hist || estado.aba !== "reuniao") return;
  const canal = reuniao.canal, conversa = reuniao.conversas[canal];
  const agente = (estado.equipe || []).find((a) => a.id === canal);
  document.getElementById("conversa-cabeca").innerHTML = `<span class="avatar-equipe">${esc(canal === "todos" ? "To" : agente?.nome.slice(0, 2))}</span>
    <div><h2>${esc(canal === "todos" ? "Todos" : agente?.nome)}</h2><p>${esc(canal === "todos" ? "Responde quem cuida do assunto." : agente?.papel)}</p></div>`;
  const mensagens = (conversa?.mensagens || []).map((m) => ({ ...m }));
  for (const f of fiosDoCanal(canal)) for (const m of f.mensagens) mensagens.push({ ...m, fio: f });
  mensagens.sort((a, b) => a.quando.localeCompare(b.quando));
  const ocupado = reuniao.enviando || conversa?.digitando;
  const p = conversa?.progresso;
  const status = p ? `${p.etapa} · ${Math.floor(p.segundos / 60)}min ${p.segundos % 60}s${p.sem_atividade_segundos >= 90 ? " · sem nova atividade há " + Math.floor(p.sem_atividade_segundos / 60) + " min" : ""}` : "A equipe está respondendo…";
  const html = mensagens.map((m) => `<article class="fala ${m.autor === "usuario" ? "minha" : "agente"} ${m.erro ? "falha" : ""}"><div class="fala-meta"><b>${esc(nomeDe(m.autor))}</b><time>${esc(hora(m.quando))}</time>${m.fio ? etiqueta(TIPOS_DAILY[m.fio.tipo] + " · " + m.fio.id, "frio") : ""}</div><p>${esc(m.texto)}</p></article>`).join("")
    || `<div class="conversa-vazia"><p class="rotulo">Sala de reunião · CANAL</p><h3>${canal === "todos" ? "Vamos conversar?" : "Fale com " + esc(agente?.nome)}</h3><p>Pergunte sobre os números do canal, peça uma análise ou uma pauta. Ele responde com o que está nos arquivos.</p></div>`;
  const chave = JSON.stringify([canal, mensagens.length, mensagens.at(-1)?.quando, ocupado, status]);
  if (hist.dataset.chave !== chave) {
    const noFim = hist.scrollHeight - hist.scrollTop - hist.clientHeight < 90 || hist.dataset.canal !== canal;
    hist.innerHTML = html + (ocupado ? `<p class="pensando">${esc(status)}</p>` : "");
    hist.dataset.chave = chave; hist.dataset.canal = canal;
    if (noFim) hist.scrollTop = hist.scrollHeight;
  }
  const campo = document.getElementById("reuniao-texto");
  if (document.activeElement !== campo) campo.value = reuniao.rascunhos[canal] || "";
  campo.placeholder = `Mensagem para ${canal === "todos" ? "a equipe" : agente?.nome}…`;
  document.getElementById("reuniao-enviar").disabled = !!ocupado;
  document.getElementById("erro-reuniao").textContent = reuniao.erro;
}

async function enviaMensagem() {
  const canal = reuniao.canal, texto = (reuniao.rascunhos[canal] || "").trim();
  if (!texto || reuniao.enviando || reuniao.conversas[canal]?.digitando) return;
  reuniao.enviando = true; reuniao.erro = ""; desenhaConversa();
  try {
    await manda("/api/chat", { canal, texto });
    reuniao.rascunhos[canal] = "";
    document.getElementById("reuniao-texto").value = "";
    await atualizaConversa();
  } catch (e) { reuniao.erro = e.message; }
  finally { reuniao.enviando = false; desenhaConversa(); }
}

document.addEventListener("input", (e) => { if (e.target.id === "reuniao-texto") reuniao.rascunhos[reuniao.canal] = e.target.value; });
document.addEventListener("submit", (e) => { if (e.target.id === "conversa-form") { e.preventDefault(); enviaMensagem(); } });
document.addEventListener("keydown", (e) => { if (e.target.id === "reuniao-texto" && e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); enviaMensagem(); } });
document.addEventListener("click", async (e) => {
  const b = e.target.closest("[data-canal]"); if (!b || estado.aba !== "reuniao") return;
  reuniao.canal = b.dataset.canal; reuniao.erro = ""; desenhaNavReuniao();
  try { await atualizaConversa(); } catch (erro) { reuniao.erro = erro.message; desenhaConversa(); }
});
setInterval(async () => {
  if (estado.aba !== "reuniao") return;
  try {
    const r = await pega("/api/chat/canais"); estado.canais = r.canais;
    await carregaDaily(); desenhaNavReuniao(); await atualizaConversa();
  } catch (e) { reuniao.erro = `Não consegui atualizar a conversa: ${e.message}`; desenhaConversa(); }
}, 2500);
