// Apresentações: galeria dos decks animados (capa, score, status) e a fila de pautas validadas.
// Só lê /api/apresentacoes; a única escrita é o status (aberta <-> gravada), via /api/apresentacao/status.
const galeria = { dados: null, ocupado: false };

async function abreApresentacoes(el) {
  galeria.dados = await pega("/api/apresentacoes");
  desenhaApresentacoes(el);
}
function etiquetaDeScore(score) {
  // O corte é 80 (D-20): a partir dele é "ok" (verde); abaixo, "aviso" (laranja). Nunca a cor de marca como status (D-44).
  return score == null ? etiqueta("sem score", "frio") : etiqueta(`score ${score}`, score >= 80 ? "ok" : "aviso");
}
function cartaoDeApresentacao(d) {
  const capa = d.capa ? `<img class="capa" src="/apresentacao/${encodeURIComponent(d.slug)}/capa.png" alt="Capa de ${esc(d.titulo)}" loading="lazy">`
    : `<div class="capa vazia"><span>${d.render && d.render.ok === false ? "render falhou" : "sem render"}</span></div>`;
  const acoes = [];
  if (d.palco) acoes.push(`<a class="botao leve" href="/apresentacao/${encodeURIComponent(d.slug)}/palco.html" target="_blank" rel="noopener noreferrer">Abrir palco</a>`);
  if (d.status === "aberta") acoes.push(`<button class="botao leve" data-apresentacao="${esc(d.slug)}" data-status="gravada">Marcar gravada</button>`);
  if (d.status === "gravada") acoes.push(`<button class="botao leve" data-apresentacao="${esc(d.slug)}" data-status="aberta">Reabrir</button>`);
  return `<article class="deck ${esc(d.status)}">${capa}<div class="deck-corpo">
    <div class="meta">${etiquetaDeScore(d.score)}${d.marca ? etiqueta(d.marca, "frio") : ""}<span>${esc(num(d.slides))} slides</span><span>${esc(dataCurta(d.criado_em))}</span></div>
    <h3>${esc(d.titulo)}</h3>${d.motivo ? `<p class="motivo">${esc(d.motivo)}</p>` : ""}
    ${d.render && d.render.avisos && d.render.avisos.length ? `<p class="aviso-render">${esc(d.render.avisos.join(" · "))}</p>` : ""}
    <div class="acoes">${acoes.join("")}</div></div></article>`;
}
function secaoDeDecks(titulo, decks, aberta) {
  const corpo = decks.length ? `<div class="galeria">${decks.map(cartaoDeApresentacao).join("")}</div>`
    : `<p class="vazio">Nenhuma apresentação ${titulo.toLowerCase()}.</p>`;
  return aberta ? `<section class="folha"><header><h2>${titulo} <span>${decks.length}</span></h2></header>${corpo}</section>`
    : `<details class="folha"><summary>${titulo} <span class="etiqueta frio">${decks.length}</span></summary>${corpo}</details>`;
}
function desenhaApresentacoes(el = document.getElementById("centro")) {
  if (estado.aba !== "apresentacoes") return;
  const g = galeria.dados || { abertas: [], gravadas: [], descartadas: [], fila: [], sem_score: [] };
  el.innerHTML = `<section class="apresentacoes"><header class="tarefas-cabeca"><div><p class="rotulo">apresentacoes/decks · ordem por score de viralização</p><h2>Apresentações</h2>
    <p>Slides animados para apresentar ao vivo. A primeira em aberto é a pauta mais quente para gravar. Gere com <code>/apresentacao</code>; valide pautas novas com <code>/pautas</code>.</p></div></header>
    ${secaoDeDecks("Em aberto", g.abertas, true)}
    ${secaoDeDecks("Gravadas", g.gravadas, false)}
    ${secaoDeDecks("Descartadas", g.descartadas, false)}
    ${g.sem_score.length ? `<p class="vazio">Sem score ainda (o validador precisa pontuar): ${g.sem_score.map(esc).join(", ")}</p>` : ""}
    <section class="folha"><header><h2>Fila de pautas validadas <span>${g.fila.length}</span></h2></header>
    ${g.fila.length ? `<table><thead><tr><th class="num">Score</th><th>Pauta</th><th>Ângulo</th><th>Origem</th></tr></thead><tbody>${g.fila.map((p) =>
      `<tr><td class="num">${etiquetaDeScore(p.score)}</td><td><b>${esc(p.titulo)}</b></td><td>${esc(p.angulo)}</td><td class="mono">${esc(p.origem)}</td></tr>`).join("")}</tbody></table>`
      : '<p class="vazio">Nenhuma pauta validada esperando deck. O validador registra com <code>python3 apresentacao.py pauta</code>.</p>'}</section></section>`;
}
document.addEventListener("click", async (e) => {
  if (estado.aba !== "apresentacoes") return;
  const b = e.target.closest("button[data-apresentacao]");
  if (!b || galeria.ocupado) return;
  galeria.ocupado = true; b.disabled = true;
  try {
    await manda("/api/apresentacao/status", { slug: b.dataset.apresentacao, status: b.dataset.status });
    galeria.dados = await pega("/api/apresentacoes");
    desenhaApresentacoes();
  } catch (erro) {
    b.disabled = false; b.textContent = "Não deu: " + erro.message;
  } finally { galeria.ocupado = false; }
});
