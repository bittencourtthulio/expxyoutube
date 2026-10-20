// Diário de decisões: o que a rotina e a equipe decidiram, por quê e como desfazer.
const diario = { tipo: "" };

async function abreDecisoes(el) {
  const lista = await pega("/api/decisoes");
  const tipos = [...new Set(lista.map((d) => d.tipo).filter(Boolean))].sort();
  const visiveis = lista.filter((d) => !diario.tipo || d.tipo === diario.tipo);
  el.innerHTML = `<section class="decisoes-pagina"><header class="tarefas-cabeca"><div><p class="rotulo">Governança · estado/decisoes.jsonl</p><h2>Decisões</h2>
    <p>Toda mudança de plano ou de harness fica registrada com o motivo, a evidência e o caminho de volta.</p></div></header>
    <div class="filtros" role="group" aria-label="Filtrar por tipo"><button data-decisao-tipo="" aria-pressed="${!diario.tipo}">Todas <span>${lista.length}</span></button>${tipos.map((t) => `<button data-decisao-tipo="${esc(t)}" aria-pressed="${diario.tipo === t}">${esc(t)}</button>`).join("")}</div>
    ${visiveis.map((d) => `<article class="decisao"><div class="meta">${etiqueta(d.tipo || "sem tipo", "marca")}<span>${esc(hora(d.quando))}</span><span>por ${esc(nomeDe(d.autor))}</span>${d.daily ? etiqueta(d.daily, "frio") : ""}</div>
      <h3>${esc(d.o_que)}</h3><p><b>Por quê:</b> ${esc(d.por_que)}</p><p><b>Evidência:</b> ${esc(d.evidencia)}</p><p><b>Como desfazer:</b> ${esc(d.como_desfazer)}</p></article>`).join("")
      || '<p class="vazio">Nenhuma decisão registrada ainda. A rotina registra com <code>python3 decisoes.py registrar</code>.</p>'}</section>`;
}
document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-decisao-tipo]"); if (!b || estado.aba !== "decisoes") return;
  diario.tipo = b.dataset.decisaoTipo; abreDecisoes(document.getElementById("centro"));
});
