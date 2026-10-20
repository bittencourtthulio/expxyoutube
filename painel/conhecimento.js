// Conhecimento: o cérebro (como crescer no YouTube) e a biblioteca (sobre o que gravar), só leitura.
const saber = { base: "cerebro", tema: "", texto: "", dados: null, achadas: null };
const NOMES_BASE = { cerebro: ["Cérebro", "Boas práticas de crescimento no YouTube, destiladas de criadores. Hipótese para testar, não regra."],
  biblioteca: ["Biblioteca", "Pautas do território (IA e programação para software house). Ponto de partida, nunca roteiro."] };

async function abreConhecimento(el) {
  saber.dados = await pega("/api/conhecimento");
  await buscaConhecimento();
  desenhaConhecimento(el);
}
async function buscaConhecimento() {
  const q = new URLSearchParams({ base: saber.base });
  if (saber.tema) q.set("tema", saber.tema);
  if (saber.texto) q.set("texto", saber.texto);
  saber.achadas = await pega("/api/conhecimento/buscar?" + q);
}
function itensDaNota(texto) {
  return String(texto || "").split("\n").filter((l) => l.trim().startsWith("-")).map((l) =>
    `<li>${esc(l.trim().slice(1).trim()).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")}</li>`).join("");
}
function desenhaConhecimento(el = document.getElementById("centro")) {
  if (estado.aba !== "conhecimento") return;
  const b = saber.dados?.[saber.base] || { canais: [], temas: [] }, [nome, descricao] = NOMES_BASE[saber.base];
  el.innerHTML = `<section class="saber"><header class="tarefas-cabeca"><div><p class="rotulo">Referência externa · ${esc(saber.base)}/</p><h2>${esc(nome)}</h2><p>${esc(descricao)}</p></div>
    <div class="filtros" role="group" aria-label="Base">${Object.keys(NOMES_BASE).map((id) => `<button data-saber-base="${id}" aria-pressed="${saber.base === id}">${NOMES_BASE[id][0]} <span>${esc(num(saber.dados?.[id]?.uteis))}</span></button>`).join("")}</div></header>
    <div class="saber-numeros">${[["Notas", b.notas], ["Destiladas", b.destiladas], ["Úteis", b.uteis], ["Canais", b.canais.length]].map(([n, v]) => `<div><b>${esc(num(v))}</b><span>${n}</span></div>`).join("")}</div>
    <div class="saber-grade"><aside><h3 class="rotulo">Canais</h3>${b.canais.map((c) => `<p class="saber-canal">${esc(c.nome || c.id)}<small>${esc(num(c.destiladas))}/${esc(num(c.notas))} destiladas${c.ativo ? "" : " · pausado"}</small></p>`).join("") || '<p class="vazio">Nenhum canal cadastrado ainda.</p>'}
      <h3 class="rotulo">Temas</h3><div class="filtros"><button data-saber-tema="" aria-pressed="${!saber.tema}">Todos</button>${b.temas.filter((t) => t.notas).map((t) => `<button data-saber-tema="${esc(t.id)}" aria-pressed="${saber.tema === t.id}">${esc(t.nome)} <span>${t.notas}</span></button>`).join("")}</div></aside>
    <div><input type="text" id="saber-texto" placeholder="Buscar no título, resumo e ${saber.base === "cerebro" ? "práticas" : "ideias"}…" value="${esc(saber.texto)}">
      <div class="saber-notas">${(saber.achadas || []).map((n) => `<article class="decisao"><div class="meta">${etiqueta(n.relevancia || "", "marca")}<span>${esc(n.canal)}</span><span>${esc(dataCurta(n.publicado_em))}</span>${(n.temas || []).map((t) => etiqueta(t, "frio")).join("")}</div>
        <h3>${n.url ? `<a href="${esc(n.url)}" target="_blank" rel="noopener noreferrer">${esc(n.titulo)}</a>` : esc(n.titulo)}</h3><p>${esc(n.resumo)}</p><ul class="saber-itens">${itensDaNota(n.itens)}</ul></article>`).join("")
        || `<p class="vazio">Nada destilado ${saber.tema ? "neste tema" : "ainda"}. A rotina ingere com <code>${saber.base}.py varrer</code> e o ${saber.base === "cerebro" ? "curador" : "bibliotecário"} destila.</p>`}</div></div></div></section>`;
}
document.addEventListener("click", async (e) => {
  if (estado.aba !== "conhecimento") return;
  const b = e.target.closest("[data-saber-base], [data-saber-tema]"); if (!b) return;
  if (b.dataset.saberBase !== undefined) { saber.base = b.dataset.saberBase; saber.tema = ""; }
  if (b.dataset.saberTema !== undefined) saber.tema = b.dataset.saberTema;
  await buscaConhecimento(); desenhaConhecimento();
});
let esperaBusca;
document.addEventListener("input", (e) => {
  if (e.target.id !== "saber-texto") return;
  saber.texto = e.target.value; clearTimeout(esperaBusca);
  esperaBusca = setTimeout(async () => { await buscaConhecimento(); desenhaConhecimento(); const c = document.getElementById("saber-texto"); c.focus(); c.setSelectionRange(c.value.length, c.value.length); }, 350);
});
