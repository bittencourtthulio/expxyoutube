const dashUI = { metrica: 'views', modo: 'semanas', ordem: 'views' };
const dashNumero = v => typeof v === 'number' && Number.isFinite(v);
const dashCurto = v => Math.abs(v) >= 1000 ? (v / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' mil' : num(v);
const dashDia = (data, delta = 0) => { const d = new Date(data + 'T12:00:00Z'); d.setUTCDate(d.getUTCDate() + delta); return d.toISOString().slice(0, 10); };
const dashPeriodo = j => j?.desde && j?.ate ? `${dataCurta(j.desde)} — ${dataCurta(dashDia(j.ate, -1))}` : 'Período indisponível';
const dashTip = texto => `data-dash-tip="${esc(texto)}" tabindex="0" role="img" aria-label="${esc(texto)}"`;
const dashLegenda = (atual, anterior) => `<div class="dash-legenda"><span><i></i>${esc(atual)}</span>${anterior ? `<span class="anterior"><i></i>${esc(anterior)}</span>` : ''}</div>`;
const DASH_METRICA = { views: { serie: 'views', nome: 'Views', semana: 'views' }, inscritos: { serie: 'inscritos_ganhos', nome: 'Inscritos ganhos', semana: 'inscritos_ganhos' } };
const DASH_DESTAQUE = ['inscritos', 'inscritos_ganhos', 'views', 'horas_assistidas', 'duracao_media', 'taxa_engajamento'];
const DASH_ORDENS = { views: 'Views', minutos: 'Minutos', taxa_engajamento: 'Engajamento', inscritos: 'Inscritos', nota: 'Nota' };

function dashTabela(colunas, linhas) {
  return `<details class="dash-dados"><summary>Ver os dados</summary><div class="dash-tabela-rolagem"><table><thead><tr>${colunas.map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${linhas.map(l => `<tr>${l.map(v => `<td>${esc(v ?? 'Sem dado')}</td>`).join('')}</tr>`).join('')}</tbody></table></div></details>`;
}
function dashSvg(titulo, largura, altura, conteudo) {
  return `<svg class="dash-svg" viewBox="0 0 ${largura} ${altura}" role="img" aria-label="${esc(titulo)}"><title>${esc(titulo)}</title>${conteudo}</svg>`;
}
function dashVazio(texto = 'Ainda não há dados suficientes para este gráfico.') { return `<div class="dash-sem-dados">${esc(texto)}</div>`; }

function dashLinhas(k) {
  const m = DASH_METRICA[dashUI.metrica], serie = k.series?.[m.serie] || [];
  if (!serie.length) return dashVazio();
  const mapa = new Map(serie.map(p => [p.dia, p.valor]));
  const comparar = dashUI.modo === 'semanas' && k.janela?.desde && k.comparado_com?.desde;
  let curvas, rotulos, linhas;
  if (comparar) {
    const datas = j => Array.from({ length: 7 }, (_, i) => dashDia(j.desde, i));
    const atual = datas(k.janela), anterior = datas(k.comparado_com);
    curvas = [{ dias: anterior, classe: 'anterior' }, { dias: atual, classe: 'atual' }];
    rotulos = atual.map(d => new Date(d + 'T12:00:00').toLocaleDateString('pt-BR', { weekday: 'short' }).replace('.', ''));
    linhas = atual.map((d, i) => [dataCurta(d), num(mapa.get(d)), dataCurta(anterior[i]), num(mapa.get(anterior[i]))]);
  } else {
    const fim = k.janela?.ate ? dashDia(k.janela.ate, -1) : serie.at(-1).dia;
    const dias = Array.from({ length: 30 }, (_, i) => dashDia(fim, i - 29));
    curvas = [{ dias, classe: 'atual' }]; rotulos = dias.map(dataCurta);
    linhas = dias.map(d => [dataCurta(d), num(mapa.get(d))]);
  }
  const w = innerWidth < 600 ? 420 : 900, h = 285, l = 60, r = 25, top = 20, bottom = 245, qtd = curvas[0].dias.length;
  const valores = curvas.flatMap(c => c.dias.map(d => mapa.get(d))).filter(dashNumero);
  if (!valores.length) return dashVazio();
  const max = Math.max(1, ...valores) * 1.12;
  const x = i => l + i * (w - l - r) / Math.max(1, qtd - 1), y = v => bottom - v / max * (bottom - top);
  let svg = Array.from({ length: 5 }, (_, i) => { const valor = max * i / 4, yy = y(valor); return `<line class="dash-grade" x1="${l}" y1="${yy}" x2="${w - r}" y2="${yy}"/><text class="dash-eixo" x="${l - 12}" y="${yy + 4}" text-anchor="end">${esc(dashCurto(Math.round(valor)))}</text>`; }).join('');
  svg += rotulos.map((d, i) => i === 0 || i === qtd - 1 || i % (comparar ? 1 : 6) === 0 ? `<text class="dash-eixo" x="${x(i)}" y="272" text-anchor="middle">${esc(d)}</text>` : '').join('');
  for (const c of curvas) {
    let path = '', aberto = false;
    c.dias.forEach((d, i) => { const v = mapa.get(d); if (!dashNumero(v)) { aberto = false; return; } path += `${aberto ? 'L' : 'M'}${x(i)},${y(v)} `; aberto = true; });
    svg += `<path class="dash-linha ${c.classe}" d="${path}"/>`;
    svg += c.dias.map((d, i) => { const v = mapa.get(d); return !dashNumero(v) ? '' : `<g ${dashTip(`${dataCurta(d)} · ${m.nome}: ${num(v)}`)}><circle class="dash-ponto ${c.classe}" cx="${x(i)}" cy="${y(v)}" r="${comparar ? 4 : 3}"/><circle class="dash-hit" cx="${x(i)}" cy="${y(v)}" r="10"/></g>`; }).join('');
  }
  return dashSvg(`${m.nome} por dia`, w, h, svg) +
    dashLegenda(comparar ? dashPeriodo(k.janela) : 'Série diária disponível', comparar ? dashPeriodo(k.comparado_com) : null) +
    `<p class="dash-nota">${comparar ? 'Cada ponto compara a mesma posição nas duas janelas de 7 dias.' : 'Últimos 30 dias até o último dia processado. Lacunas indicam dias sem dado.'} Dias no fuso do Pacífico, o dia da YouTube Analytics, que atrasa de 48 a 72 horas.</p>` +
    dashTabela(comparar ? ['Dia atual', 'Valor', 'Dia anterior', 'Valor'] : ['Dia', 'Valor'], linhas);
}

function dashSemanas(d) {
  const m = DASH_METRICA[dashUI.metrica], campo = m.semana, semanas = d.semanas || [];
  if (!semanas.length) return dashVazio();
  const max = Math.max(1, ...semanas.map(s => s[campo]).filter(dashNumero)) * 1.2, w = 440, h = 285, bottom = 232;
  let svg = [0, .5, 1].map(f => `<line class="dash-grade" x1="42" x2="432" y1="${bottom - f * 195}" y2="${bottom - f * 195}"/><text class="dash-eixo" x="34" y="${bottom - f * 195 + 4}" text-anchor="end">${esc(dashCurto(Math.round(max * f)))}</text>`).join('');
  svg += semanas.map((s, i) => { const valor = s[campo], x = 66 + i * 94, altura = dashNumero(valor) ? valor / max * 195 : 0;
    const tip = `${dashPeriodo(s)} · ${dashNumero(valor) ? num(valor) : 'Sem dado completo'} · ${s[campo + '_dias']}/7 dias`;
    return `<g ${dashTip(tip)}><rect class="dash-barra ${i === semanas.length - 1 ? 'atual' : 'anterior'}" x="${x}" y="${bottom - altura}" width="48" height="${altura}" rx="5"/><text class="dash-valor" x="${x + 24}" y="${bottom - altura - 10}" text-anchor="middle">${dashNumero(valor) ? esc(dashCurto(valor)) : '—'}</text><text class="dash-eixo" x="${x + 24}" y="257" text-anchor="middle">${esc(dataCurta(s.desde))}</text></g>`;
  }).join('');
  return dashSvg('Comparação de quatro semanas', w, h, svg) + `<p class="dash-nota">Soma dos sete dias de cada semana. Semana com dia faltando fica sem valor.</p>` +
    dashTabela(['Semana', m.nome, 'Dias disponíveis'], semanas.map(s => [dashPeriodo(s), num(s[campo]), `${s[campo + '_dias']}/7`]));
}

function dashBarrasDuplas(itens, titulo, k, nomeDe) {
  if (!itens.some(i => dashNumero(i.atual) || dashNumero(i.anterior))) return dashVazio('A coleta ainda não traz esses números nas duas semanas.');
  const max = Math.max(1, ...itens.flatMap(i => [i.atual, i.anterior]).filter(dashNumero)), w = innerWidth < 600 ? 440 : 690, linha = 57, h = itens.length * linha + 24;
  const svg = itens.map((v, i) => { const y = 16 + i * linha; return `<text class="dash-categoria" x="0" y="${y + 20}">${esc(nomeDe(v))}</text>` + ['anterior', 'atual'].map((campo, n) => {
    const valor = v[campo], largura = dashNumero(valor) ? valor / max * (w - 215) : 0, yy = y + n * 18;
    return `<g ${dashTip(`${nomeDe(v)} · ${campo === 'atual' ? 'Semana atual' : 'Semana anterior'}: ${num(valor)}`)}><rect class="dash-barra ${campo}" x="165" y="${yy}" width="${largura}" height="12" rx="3"/><text class="dash-eixo" x="${175 + largura}" y="${yy + 10}">${esc(num(valor))}</text></g>`;
  }).join(''); }).join('');
  return dashLegenda(dashPeriodo(k.janela), dashPeriodo(k.comparado_com)) + dashSvg(titulo, w, h, svg) +
    dashTabela(['Item', 'Semana atual', 'Semana anterior'], itens.map(i => [nomeDe(i), num(i.atual), num(i.anterior)]));
}

function dashFormatos(d) {
  const formatos = d.formatos || [];
  if (!formatos.length) return dashVazio('A coleta ainda não separa Shorts de vídeos nesta semana.');
  const total = formatos.reduce((s, f) => s + (dashNumero(f.views) ? f.views : 0), 0);
  return `<div class="dash-formatos-lista">${formatos.map(f => { const fatia = total && dashNumero(f.views) ? f.views / total * 100 : 0;
    return `<div class="dash-formato"><h4>${esc(f.rotulo)}</h4><div class="fatia" ${dashTip(`${f.rotulo}: ${num(Math.round(fatia))}% das views`)}><i style="width:${fatia.toFixed(1)}%"></i></div><dl>
      <dt>Views</dt><dd>${esc(num(f.views))}</dd><dt>Semana anterior</dt><dd>${esc(num(f.views_anterior))}</dd>
      <dt>Minutos assistidos</dt><dd>${esc(num(f.minutos))}</dd><dt>Engajamento por view</dt><dd>${dashNumero(f.taxa_engajamento) ? esc(num(f.taxa_engajamento)) + '%' : '–'}</dd>
      <dt>Inscritos ganhos</dt><dd>${esc(num(f.inscritos))}</dd></dl></div>`; }).join('')}</div>
    <p class="dash-nota">Tipo de conteúdo informado pela YouTube Analytics (creatorContentType). Engajamento = curtidas, comentários e compartilhamentos sobre views.</p>`;
}

function dashTopVideos(d) {
  const videos = [...(d.top_videos || [])];
  if (!videos.length) return dashVazio('Nenhum vídeo com métricas nesta análise.');
  const campo = dashUI.ordem;
  videos.sort((a, b) => (dashNumero(b[campo]) ? b[campo] : -1) - (dashNumero(a[campo]) ? a[campo] : -1));
  const cab = (c, rotulo) => `<th class="num ordena" data-dash-ordem="${c}" ${campo === c ? 'aria-sort="descending"' : ''} tabindex="0">${rotulo}</th>`;
  return `<div class="dash-tabela-rolagem"><table class="dash-posts"><thead><tr><th>Vídeo</th>${cab('views', 'Views')}${cab('minutos', 'Minutos')}<th class="num">% assistido</th>${cab('taxa_engajamento', 'Engaj.')}${cab('inscritos', 'Inscritos')}${cab('nota', 'Nota')}</tr></thead><tbody>${videos.map((v, i) => `<tr><td><span class="dash-posicao">${i + 1}</span>${v.link ? `<a href="${esc(v.link)}" target="_blank" rel="noopener noreferrer">${esc(v.titulo || 'Ver vídeo')}</a>` : esc(v.titulo || 'Vídeo')}<small>${esc(v.publicado_em ? dataCurta(v.publicado_em) : '')} · <span class="formato">${esc(v.formato === 'SHORTS' ? 'Short' : 'Vídeo')}</span></small></td><td class="num"><b>${esc(num(v.views))}</b></td><td class="num">${esc(num(v.minutos))}</td><td class="num">${dashNumero(v.pct_assistido) ? esc(num(v.pct_assistido)) + '%' : '–'}</td><td class="num">${dashNumero(v.taxa_engajamento) ? esc(num(v.taxa_engajamento)) + '%' : '–'}</td><td class="num">${esc(num(v.inscritos))}</td><td class="num">${esc(num(v.nota))}</td></tr>`).join('')}</tbody></table></div><p class="dash-nota">Os 10 vídeos com mais views nos últimos 28 dias; clique no cabeçalho para reordenar. Nota 0 a 10 contra a mediana do mesmo formato.</p>`;
}

function desenhaPainel(el) {
  const r = estado.kpis;
  if (!r?.kpis) { el.innerHTML = `<div class="dash-cabeca"><div><p class="rotulo">YouTube · Visão geral</p><h2>Painel</h2><p>Os indicadores aparecem depois da primeira coleta e do diagnóstico: <code>.venv/bin/python editorial/analises/coletar_youtube.py</code> e <code>.venv/bin/python editorial/analises/diagnostico.py</code>.</p></div></div>`; return; }
  const k = r.kpis, d = r.dashboard || {}, todos = [...(k.basicas || []), ...(k.performance || [])], porId = Object.fromEntries(todos.map(x => [x.id, x]));
  const extras = todos.filter(x => !DASH_DESTAQUE.includes(x.id));
  const t30 = k.trinta_dias || {}, coletado = r.coletado_em ? new Date(r.coletado_em).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : 'não informada';
  const m = DASH_METRICA[dashUI.metrica];
  el.innerHTML = `<div class="dashboard"><header class="dash-cabeca"><div><p class="rotulo">YouTube · Visão geral</p><h2>${esc(r.canal?.titulo || 'Canal')}</h2><p>${esc(r.canal?.handle || '')}${r.tese ? ' · ' + esc(r.tese) : ' · Acompanhe o crescimento, compare as semanas e veja o que traz audiência.'}</p></div><div class="dash-periodo"><b>${esc(dashPeriodo(k.janela))}</b><span>Comparado com ${esc(dashPeriodo(k.comparado_com))}</span><small>Última coleta: ${esc(coletado)}</small></div></header>
    <div class="dash-kpis">${DASH_DESTAQUE.map(id => porId[id] ? cartaoKpi(porId[id]) : '').join('')}</div>
    <div class="dash-secao"><div><p class="rotulo">Evolução do canal</p><h3>Um dia de cada vez</h3></div><div class="dash-controles" role="group" aria-label="Métrica dos gráficos de evolução">${Object.entries(DASH_METRICA).map(([id, x]) => `<button data-dash-metrica="${id}" aria-pressed="${dashUI.metrica === id}">${x.nome}</button>`).join('')}</div></div>
    <div class="dash-grade-graficos"><section class="dash-card dash-evolucao"><header><div><h3>${m.nome} por dia</h3><p>${dashUI.modo === 'semanas' ? 'Duas semanas na mesma escala' : 'Histórico diário do canal'}</p></div><div class="dash-controles compacto"><button data-dash-modo="semanas" aria-pressed="${dashUI.modo === 'semanas'}">Comparar semanas</button><button data-dash-modo="historico" aria-pressed="${dashUI.modo === 'historico'}">30 dias</button></div></header>${dashLinhas(k)}</section>
    <section class="dash-card dash-semanas"><header><div><h3>Quatro semanas em perspectiva</h3><p>${m.nome} por semana</p></div></header>${dashSemanas(d)}</section>
    <section class="dash-card dash-interacoes"><header><div><h3>Como as pessoas interagem</h3><p>Semana atual × semana anterior · canal inteiro</p></div></header>${dashBarrasDuplas(d.interacoes || [], 'Interações do canal: semana atual e anterior', k, i => i.nome)}</section>
    <section class="dash-card dash-trafego"><header><div><h3>De onde vêm as views</h3><p>Origem do tráfego · semana atual × anterior</p></div><span class="etiqueta frio">${esc(dashPeriodo(k.janela))}</span></header>${dashBarrasDuplas((d.trafego || []).slice(0, 7), 'Origem das views: semana atual e anterior', k, t => t.rotulo)}</section>
    <section class="dash-card dash-formatos"><header><div><h3>Shorts × vídeos</h3><p>O que cada formato entregou na semana</p></div></header>${dashFormatos(d)}</section></div>
    <div class="dash-secao"><div><p class="rotulo">Conteúdo em destaque</p><h3>Os vídeos que mais trouxeram audiência</h3></div><div class="dash-controles compacto" role="group" aria-label="Ordem dos vídeos">${Object.entries(DASH_ORDENS).map(([id, nome]) => `<button data-dash-ordem="${id}" aria-pressed="${dashUI.ordem === id}">${nome}</button>`).join('')}</div></div><section class="dash-card">${dashTopVideos(d)}</section>
    <div class="dash-secao"><div><p class="rotulo">Panorama de 30 dias</p><h3>Além da última semana</h3></div></div><div class="dash-mensal">${[['views', 'Views'], ['horas_assistidas', 'Horas assistidas'], ['inscritos_ganhos', 'Inscritos ganhos'], ['interacoes', 'Interações']].map(([id, nome]) => `<div><span>${nome}</span><b>${esc(num(t30[id]))}</b><small>Últimos 30 dias processados</small></div>`).join('')}</div>
    <details class="dash-extra"><summary>Mais indicadores do canal <span>${extras.length}</span></summary><div class="kpis">${extras.map(cartaoKpi).join('')}</div></details><p class="dash-fonte">Fonte: YouTube Analytics API e YouTube Data API na última coleta. ${k.recusadas?.length ? 'Métricas indisponíveis: ' + esc(k.recusadas.join(', ')) + '.' : ''}</p></div>`;
}

document.addEventListener('click', e => {
  const alvo = e.target.closest('[data-dash-metrica], [data-dash-modo], [data-dash-ordem]'); if (!alvo || estado.aba !== 'painel') return;
  if (alvo.dataset.dashMetrica) dashUI.metrica = alvo.dataset.dashMetrica;
  if (alvo.dataset.dashModo) dashUI.modo = alvo.dataset.dashModo;
  if (alvo.dataset.dashOrdem) dashUI.ordem = alvo.dataset.dashOrdem;
  desenhaPainel(document.getElementById('centro'));
});
function mostraDicaDash(alvo, x, y) {
  let dica = document.getElementById('dash-tooltip');
  if (!dica) { dica = document.createElement('div'); dica.id = 'dash-tooltip'; dica.setAttribute('role', 'tooltip'); document.body.append(dica); }
  dica.textContent = alvo.dataset.dashTip; dica.hidden = false;
  dica.style.left = Math.max(8, Math.min(x + 12, innerWidth - dica.offsetWidth - 10)) + 'px';
  dica.style.top = Math.max(8, Math.min(y + 14, innerHeight - dica.offsetHeight - 10)) + 'px';
}
document.addEventListener('pointermove', e => { const t = e.target.closest('[data-dash-tip]'); if (t) mostraDicaDash(t, e.clientX, e.clientY); else document.getElementById('dash-tooltip')?.setAttribute('hidden', ''); });
document.addEventListener('focusin', e => { const t = e.target.closest('[data-dash-tip]'); if (t) { const r = t.getBoundingClientRect(); mostraDicaDash(t, r.x + r.width / 2, r.y); } else document.getElementById('dash-tooltip')?.setAttribute('hidden', ''); });
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') document.getElementById('dash-tooltip')?.setAttribute('hidden', '');
  if (e.key === 'Enter' && e.target.dataset?.dashOrdem) e.target.click();
});
window.addEventListener('scroll', () => document.getElementById('dash-tooltip')?.setAttribute('hidden', ''), true);
matchMedia('(max-width: 599px)').addEventListener('change', () => { if (estado.aba === 'painel') desenhaPainel(document.getElementById('centro')); });
