// Kanban da daily: o estado vem do log (estado/daily.jsonl) e toda mudança passa pelo servidor.
const COLUNAS_TAREFAS = [
  ["pendente", "Pendente", "Na fila da rotina"],
  ["executando", "Executando", "Trabalho em andamento"],
  ["aguardando-resposta", "Aguardando você", "A equipe precisa de uma resposta"],
  ["finalizado", "Finalizado", "Concluídos e encerrados"],
];
const quadro = { aberta: null, arrastando: null, salvando: false, erro: "", aviso: "", tipo: "tarefa" };
const encerradoDaily = (f) => ["cancelada", "revogada", "finalizada"].includes(f.status);
const tituloTarefa = (f) => f.titulo || ((f.texto || "").split(/[\n.!?]/)[0].trim().slice(0, 80) || TIPOS_DAILY[f.tipo]);
const dataBr = (d) => d ? d.split("-").reverse().join("/") : "a definir";

async function abreTarefas(el) {
  await Promise.all([carregaDaily(), carregaEquipe()]);
  desenhaTarefas(el);
}

function formularioNovo() {
  const para = [["ambos", "Analista e planejador"], ["todos", "Toda a equipe"], ...(estado.equipe || []).map((a) => [a.id, a.nome])];
  return `<form class="novo-pedido" id="novo-pedido"><div class="tipos-pedido" role="group" aria-label="Tipo do pedido">${Object.entries(TIPOS_DAILY).map(([id, nome]) =>
    `<button type="button" data-tipo-pedido="${id}" aria-pressed="${quadro.tipo === id}">${nome}</button>`).join("")}</div>
    <p class="dica-pedido">${esc(DICAS_DAILY[quadro.tipo])}</p>
    <div class="linha-pedido"><input type="text" id="pedido-titulo" maxlength="120" placeholder="Título (opcional)"><select id="pedido-para" aria-label="Para quem">${para.map(([id, nome]) => `<option value="${esc(id)}">${esc(nome)}</option>`).join("")}</select></div>
    <textarea id="pedido-texto" placeholder="Escreva o pedido para a equipe…" required></textarea>
    <div class="linha-pedido"><input type="text" id="pedido-serie" placeholder="Recorte opcional: shorts, video-longo ou nome de playlist"><button class="botao" type="submit">Registrar na daily</button></div></form>`;
}

function desenhaTarefas(el = document.getElementById("centro")) {
  if (estado.aba !== "tarefas" || quadro.arrastando) return;
  const itens = estado.daily?.itens || [];
  const campo = document.getElementById("pedido-texto"), rascunho = campo ? { t: campo.value, ti: document.getElementById("pedido-titulo").value } : null;
  el.innerHTML = `<section class="tarefas-pagina"><header class="tarefas-cabeca"><div><p class="rotulo">Daily · Fluxo de trabalho</p><h2>Tarefas</h2>
    <p>O que você pede aqui a rotina da manhã lê, executa ou estrutura no harness, e responde no mesmo fio.</p></div></header>
    ${formularioNovo()}<p class="erro-carga" role="alert">${esc(quadro.erro)}</p><p class="tarefa-feedback" role="status">${esc(quadro.aviso)}</p>
    <div class="tarefas-kanban">${COLUNAS_TAREFAS.map(([id, nome, dica]) => { const doEstado = itens.filter((f) => f.situacao === id);
      return `<section class="tarefas-coluna" data-estado="${id}" aria-label="${nome}"><header><h3>${nome}</h3><span>${doEstado.length}</span></header><p class="coluna-dica">${dica}</p>
      <div class="tarefas-cartoes">${doEstado.map((f) => `<button type="button" class="tarefa-cartao" draggable="true" data-tarefa="${esc(f.id)}"><span class="tarefa-meta"><span>${esc(TIPOS_DAILY[f.tipo])}</span><span>${esc(f.id)}</span></span>
        <strong class="tarefa-titulo">${esc(tituloTarefa(f))}</strong><span class="tarefa-para">para ${esc(nomeDe(f.para))}${f.serie ? " · " + esc(f.serie) : ""}</span>
        <span class="tarefa-rodape">${etiqueta(f.status)}<time datetime="${esc(f.atualizado_em)}">${esc(hora(f.atualizado_em))}</time></span></button>`).join("") || '<p class="tarefa-vazia">Nada nesta etapa.</p>'}</div></section>`; }).join("")}</div></section>`;
  if (rascunho) { document.getElementById("pedido-texto").value = rascunho.t; document.getElementById("pedido-titulo").value = rascunho.ti; }
}

function dialogoTarefa() {
  let d = document.getElementById("detalhe-tarefa");
  if (!d) {
    d = document.createElement("dialog"); d.id = "detalhe-tarefa"; d.className = "detalhe-tarefa";
    document.body.append(d);
    d.addEventListener("close", () => { quadro.aberta = null; });
  }
  return d;
}

function desenhaDetalhe() {
  const f = (estado.daily?.itens || []).find((x) => x.id === quadro.aberta); if (!f) return;
  const d = dialogoTarefa(), resposta = document.getElementById("detalhe-resposta")?.value || "";
  const pensando = (estado.daily.pensando || []).includes(f.id);
  d.innerHTML = `<header class="detalhe-cabeca"><div><p class="rotulo">${esc(f.id)} · ${esc(TIPOS_DAILY[f.tipo])} · para ${esc(nomeDe(f.para))}</p><h2>${esc(tituloTarefa(f))}</h2></div>
    <button class="botao leve" data-fechar-detalhe="1" aria-label="Fechar">×</button></header>
    <p class="detalhe-estado">${etiqueta(f.status)} ${f.regra_em_vigor ? etiqueta("regra em vigor", "marca") : ""} ${f.onde ? `<span class="detalhe-onde">aplicado em ${esc(f.onde)}</span>` : ""}</p>
    <div class="detalhe-conversa">${f.mensagens.map((m) => `<article class="fala ${m.autor === "usuario" ? "minha" : "agente"}"><div class="fala-meta"><b>${esc(nomeDe(m.autor))}</b><time>${esc(hora(m.quando))}</time>${m.ao_vivo ? etiqueta("ao vivo", "frio") : ""}</div><p>${esc(m.texto)}</p></article>`).join("")}
    ${pensando ? '<p class="pensando">A equipe está lendo os arquivos para responder…</p>' : ""}</div>
    ${encerradoDaily(f) ? '<p class="vazio">Este fio está encerrado.</p>' : `<form id="detalhe-form"><textarea id="detalhe-resposta" placeholder="Sua resposta neste fio…"></textarea>
      <div class="detalhe-acoes"><button class="botao" type="submit">Responder</button><button class="botao leve" type="button" data-ao-vivo="${esc(f.id)}" ${pensando ? "disabled" : ""}>Pedir resposta agora</button>
      <select id="detalhe-mover" aria-label="Mover para">${COLUNAS_TAREFAS.map(([id, nome]) => `<option value="${id}" ${f.situacao === id ? "selected" : ""}>${nome}</option>`).join("")}</select>
      <button class="botao leve" type="button" data-finalizar="${esc(f.id)}">Finalizar</button><button class="botao leve" type="button" data-encerrar="${esc(f.id)}">${f.tipo === "nao-fazer" || f.tipo === "aprendizado" ? "Revogar" : "Cancelar"}</button></div>
      <p class="erro-carga" id="detalhe-erro" role="alert"></p></form>`}`;
  const campo = document.getElementById("detalhe-resposta"); if (campo) campo.value = resposta;
}

async function acaoNoFio(rota, corpo, depois) {
  const erro = document.getElementById("detalhe-erro");
  try { await manda(rota, corpo); if (depois) await depois(); await carregaDaily(); desenhaTarefas(); desenhaDetalhe(); }
  catch (e) { if (erro) erro.textContent = e.message; else { quadro.erro = e.message; desenhaTarefas(); } }
}

async function moveTarefa(id, coluna) {
  const f = (estado.daily?.itens || []).find((x) => x.id === id);
  if (!f || f.situacao === coluna) return;
  quadro.erro = ""; quadro.aviso = "Salvando…"; desenhaTarefas();
  try {
    await manda("/api/tarefa/mover", { id, coluna, revisao: f.revisao });
    quadro.aviso = `${id} movida para ${COLUNAS_TAREFAS.find(([c]) => c === coluna)[1]}.`;
  } catch (e) { quadro.aviso = ""; quadro.erro = e.message; }
  await carregaDaily(); desenhaTarefas(); desenhaDetalhe();
}

document.addEventListener("click", async (e) => {
  if (estado.aba !== "tarefas") return;
  const b = e.target.closest("button"); if (!b) return; const d = b.dataset;
  if (d.tipoPedido) { quadro.tipo = d.tipoPedido; desenhaTarefas(); }
  if (d.tarefa) { quadro.aberta = d.tarefa; desenhaDetalhe(); dialogoTarefa().showModal(); }
  if (d.fecharDetalhe) dialogoTarefa().close();
  if (d.aoVivo) acaoNoFio("/api/ao-vivo", { id: d.aoVivo });
  if (d.finalizar) acaoNoFio("/api/finalizar", { id: d.finalizar });
  if (d.encerrar && confirmaEncerrar(d.encerrar)) acaoNoFio("/api/encerrar", { id: d.encerrar });
});
function confirmaEncerrar(id) {
  const erro = document.getElementById("detalhe-erro");
  const botao = document.querySelector(`[data-encerrar="${id}"]`);
  if (botao && !botao.dataset.confirmar) { botao.dataset.confirmar = "1"; botao.textContent = "Confirmar"; if (erro) erro.textContent = "Clique de novo para confirmar o encerramento."; return false; }
  return true;
}
document.addEventListener("submit", async (e) => {
  if (e.target.id === "novo-pedido") {
    e.preventDefault();
    const texto = document.getElementById("pedido-texto").value.trim(); if (!texto) return;
    quadro.erro = "";
    try {
      const r = await manda("/api/novo", { tipo: quadro.tipo, texto, titulo: document.getElementById("pedido-titulo").value.trim() || null,
        para: document.getElementById("pedido-para").value, serie: document.getElementById("pedido-serie").value.trim() || null });
      document.getElementById("pedido-texto").value = ""; document.getElementById("pedido-titulo").value = "";
      quadro.aviso = `${r.id} registrado na daily.`;
    } catch (erro) { quadro.erro = erro.message; }
    await carregaDaily(); desenhaTarefas();
  }
  if (e.target.id === "detalhe-form") {
    e.preventDefault();
    const texto = document.getElementById("detalhe-resposta").value.trim(); if (!texto) return;
    document.getElementById("detalhe-resposta").value = "";
    acaoNoFio("/api/responder", { id: quadro.aberta, texto });
  }
});
document.addEventListener("change", (e) => { if (e.target.id === "detalhe-mover") moveTarefa(quadro.aberta, e.target.value); });
document.addEventListener("dragstart", (e) => {
  const card = e.target.closest?.("[data-tarefa]"); if (!card) return;
  quadro.arrastando = card.dataset.tarefa; e.dataTransfer.setData("text/plain", quadro.arrastando); e.dataTransfer.effectAllowed = "move";
  card.classList.add("arrastando-tarefa");
});
function sobreColuna(e) {
  const coluna = e.target.closest?.(".tarefas-coluna"); if (!coluna || !quadro.arrastando) return;
  e.preventDefault();
  document.querySelectorAll(".recebe-tarefa").forEach((c) => c.classList.remove("recebe-tarefa"));
  coluna.classList.add("recebe-tarefa");
}
document.addEventListener("dragenter", sobreColuna);
document.addEventListener("dragover", sobreColuna);
document.addEventListener("dragend", () => { quadro.arrastando = null; document.querySelectorAll(".recebe-tarefa, .arrastando-tarefa").forEach((c) => c.classList.remove("recebe-tarefa", "arrastando-tarefa")); });
document.addEventListener("drop", (e) => {
  const coluna = e.target.closest?.(".tarefas-coluna"); if (!coluna || !quadro.arrastando) return;
  e.preventDefault(); const id = quadro.arrastando; quadro.arrastando = null; moveTarefa(id, coluna.dataset.estado);
});
setInterval(async () => {
  if (estado.aba !== "tarefas" || quadro.arrastando || document.activeElement?.matches?.("textarea, input")) return;
  try { await carregaDaily(); desenhaTarefas(); if (quadro.aberta) desenhaDetalhe(); } catch (e) { /* tenta de novo no próximo ciclo */ }
}, 6000);
