const centralRelatorios = {dados: null, id: 'visao-geral', data: '', busca: '', filtro: '', ordem: null, sentido: 1, pagina: 0, requisicao: 0};
const relTexto = v => v == null ? '—' : typeof v === 'boolean' ? (v ? 'Sim' : 'Não') : typeof v === 'object' ? JSON.stringify(v) : String(v);
const relNumero = v => typeof v === 'number' && Number.isFinite(v);
const relNormaliza = s => String(s).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const relAtual = () => centralRelatorios.dados?.relatorios.find(r => r.id === centralRelatorios.id);
const relData = s => s ? new Date(s.length === 10 ? s + 'T12:00:00' : s).toLocaleString('pt-BR', s.length === 10 ? {dateStyle: 'short'} : {dateStyle: 'short', timeStyle: 'short'}) : 'Não disponível';
function abreRelatorios() { return carregaRelatorios(false); }
async function carregaRelatorios(forcar = false) {
  if (estado.aba !== 'relatorios') return;
  if (centralRelatorios.dados && !forcar) { desenhaCentralRelatorios(); return; }
  const requisicao = ++centralRelatorios.requisicao;
  document.getElementById('centro').innerHTML = '<div class="rel-carregando" role="status">Preparando os relatórios a partir dos registros do projeto…</div>';
  try {
    const dados = await pega('/api/relatorios' + (centralRelatorios.data ? '?data=' + encodeURIComponent(centralRelatorios.data) : ''));
    if (requisicao !== centralRelatorios.requisicao) return;
    centralRelatorios.dados = dados; centralRelatorios.data = dados.data;
    if (estado.aba === 'relatorios') desenhaCentralRelatorios();
  } catch (e) {
    if (estado.aba === 'relatorios' && requisicao === centralRelatorios.requisicao)
      document.getElementById('centro').innerHTML = `<div class="rel-carregando"><p class="erro" role="alert">Não consegui carregar os relatórios: ${esc(e.message)}</p><button class="botao" data-rel-atualizar="1">Tentar novamente</button></div>`;
  }
}
function desenhaCentralRelatorios() {
  const d = centralRelatorios.dados;
  document.getElementById('centro').innerHTML = `<div class="rel-central"><aside class="rel-lateral" aria-label="Catálogo de relatórios"><header><p class="rotulo">Inteligência do canal</p><h2>Relatórios<span>${d.relatorios.length}</span></h2><p>Uma leitura para cada decisão.</p></header><label for="rel-busca" class="sr-rel">Buscar relatório</label><input id="rel-busca" type="search" placeholder="Buscar relatório…" value="${esc(centralRelatorios.busca)}"><nav id="rel-nav" aria-label="Relatórios por categoria"></nav><footer>Dados locais · Sem nova coleta<br>Atualizado ${esc(relData(d.gerado_em))}</footer></aside><section class="rel-conteudo"><div class="rel-ferramentas"><label for="rel-data">Base de análise <select id="rel-data">${d.datas.map(data => `<option value="${esc(data)}" ${data===d.data?'selected':''}>${esc(relData(data))}</option>`).join('')}</select></label><div><button class="botao leve" data-rel-atualizar="1">Atualizar</button><button class="botao leve" data-rel-csv="1">Exportar CSV</button><button class="botao leve" data-rel-imprimir="1">Imprimir</button></div></div><article id="rel-documento" aria-live="polite"></article></section></div>`;
  desenhaMenuRelatorios(); desenhaDocumentoRelatorio();
}
function desenhaMenuRelatorios() {
  const d = centralRelatorios.dados, grupos = new Map(), busca = relNormaliza(centralRelatorios.busca);
  for (const r of d.relatorios) {
    if (!relNormaliza(r.titulo + ' ' + r.categoria + ' ' + r.descricao).includes(busca)) continue;
    if (!grupos.has(r.categoria)) grupos.set(r.categoria, []);
    grupos.get(r.categoria).push(r);
  }
  document.getElementById('rel-nav').innerHTML = [...grupos].map(([nome, rs]) => `<details class="rel-grupo" ${busca || rs.some(r => r.id===centralRelatorios.id) ? 'open' : ''}><summary>${esc(nome)}<span>${rs.length}</span></summary>${rs.map(r => `<button data-rel-id="${esc(r.id)}" aria-current="${r.id===centralRelatorios.id ? 'page' : 'false'}"><span>${esc(r.titulo)}</span>${r.linhas.length ? '' : '<small>Sem registros</small>'}</button>`).join('')}</details>`).join('') || '<p class="vazio">Nenhum relatório encontrado.</p>';
}
function relValor(v, c) {
  if (c.formato === 'link') {
    if (typeof v === 'string' && /^\/relatorio\/\d{4}-\d{2}-\d{2}\/diagnostico\.html$/.test(v)) return `<a href="${esc(v)}" target="_blank" rel="noopener">Abrir relatório ↗</a>`;
    try { const u = new URL(v); if (u.protocol === 'https:') return `<a href="${esc(u.href)}" target="_blank" rel="noopener noreferrer">Abrir ↗</a>`; } catch {}
    return '—';
  }
  if (relNumero(v)) return esc(num(v)) + (c.formato === 'percentual' ? '%' : '');
  return esc(relTexto(v));
}
function graficoRelatorio(r) {
  const g = r.grafico; if (!g) return '';
  const validos = r.linhas.filter(p => relNumero(p[g.y]) && (g.tipo !== 'dispersao' || relNumero(p[g.x])));
  if (!validos.length) return '<p class="rel-sem-grafico">Sem valores medidos para desenhar o gráfico.</p>';
  const nomeY = r.colunas.find(c => c.key===g.y)?.label || g.y;
  if (g.tipo === 'barras') {
    const pontos = validos.slice(0, 12), max = Math.max(1, ...pontos.map(p => Math.abs(p[g.y])));
    return `<section class="rel-grafico"><h3>${esc(g.titulo || nomeY)}</h3><div class="rel-barras">${pontos.map(p => `<div class="rel-barra" title="${esc(relTexto(p[g.x]))}: ${esc(num(p[g.y]))}"><span>${esc(relTexto(p[g.x]))}</span><div><i style="width:${Math.abs(p[g.y])/max*100}%"></i></div><b>${esc(num(p[g.y]))}</b></div>`).join('')}</div>${validos.length > 12 ? '<p>Gráfico com os 12 primeiros registros. A tabela contém a lista completa.</p>' : ''}</section>`;
  }
  const W=880,H=230,L=64,R=18,T=15,B=42, max=Math.max(1,...validos.map(p=>p[g.y]));
  const linhas = r.linhas;
  const xs = g.tipo==='dispersao' ? validos.map(p=>p[g.x]) : linhas.map((_,i)=>i);
  const xmin = Math.min(...xs), xmax = Math.max(xmin+1,...xs);
  const x = n => L+(n-xmin)/(xmax-xmin)*(W-L-R), y = n => H-B-n/max*(H-T-B);
  let anterior = null, caminho = '';
  const pontos = (g.tipo==='dispersao' ? validos : linhas).map((p,i) => {
    if (!relNumero(p[g.y])) { anterior=null; return ''; }
    const px = x(g.tipo==='dispersao'?p[g.x]:i), py=y(p[g.y]);
    const gap = anterior && /^\d{4}-\d{2}-\d{2}$/.test(p[g.x]) && (new Date(p[g.x])-new Date(anterior[g.x])) > 86400000;
    caminho += `${anterior && !gap ? 'L' : 'M'}${px},${py} `; anterior=p;
    return `<circle cx="${px}" cy="${py}" r="${g.tipo==='dispersao'?5:3}" tabindex="0"><title>${esc(relTexto(p[g.x]))}: ${esc(num(p[g.y]))}${p.nome ? ' · '+esc(p.nome) : ''}</title></circle>`;
  }).join('');
  const ticks = [0,.5,1].map(t=>`<line x1="${L}" x2="${W-R}" y1="${y(max*t)}" y2="${y(max*t)}"/><text x="${L-10}" y="${y(max*t)+4}" text-anchor="end">${esc(num(max*t))}</text>`).join('');
  const labels = g.tipo==='dispersao' ? [xmin,xmax] : [linhas[0]?.[g.x],linhas.at(-1)?.[g.x]];
  return `<section class="rel-grafico"><h3>${esc(nomeY)}</h3><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(nomeY)}; valores completos na tabela abaixo"><title>${esc(r.titulo)}</title>${ticks}${g.tipo==='linha'?`<path d="${caminho}"/>`:''}${pontos}<text x="${L}" y="${H-10}">${esc(relTexto(labels[0]))}</text><text x="${W-R}" y="${H-10}" text-anchor="end">${esc(relTexto(labels[1]))}</text></svg><p>${g.tipo==='dispersao'?'Eixo horizontal: '+esc(r.colunas.find(c=>c.key===g.x)?.label || g.x)+'. Cada ponto é um dia.':'Passe sobre os pontos para ver os valores. Lacunas não são preenchidas.'}</p></section>`;
}
function desenhaDocumentoRelatorio() {
  const r = relAtual(); if (!r) return;
  const d = centralRelatorios.dados;
  document.getElementById('rel-documento').innerHTML = `<header class="rel-cabeca"><p class="rotulo">${esc(r.categoria)}</p><h1>${esc(r.titulo)}</h1><p class="rel-descricao">${esc(r.descricao)}</p><div class="rel-metadados"><span>${r.escopo==='atual' ? 'Estado atual da operação' : 'Base de análise: '+esc(relData(r.data_base))}</span><span>${r.linhas.length} registros</span><span>${r.escopo==='atual'?'Atualização: '+esc(relData(d.gerado_em)):'Coleta de métricas: '+esc(relData(r.coletado_em))}</span></div></header>${d.avisos.length?`<div class="rel-aviso">${d.avisos.map(esc).join('<br>')}</div>`:''}${r.kpis.length?`<div class="rel-kpis">${r.kpis.map(k=>`<div><span>${esc(k.nome)}</span><strong>${esc(num(k.valor))}</strong></div>`).join('')}</div>`:''}${r.textos.filter(Boolean).length?`<section class="rel-leitura"><h2>Leitura da análise</h2>${r.textos.filter(Boolean).map(t=>`<p>${esc(t)}</p>`).join('')}</section>`:''}${graficoRelatorio(r)}<section class="rel-dados"><header><h2>Dados do relatório</h2><label><span class="sr-rel">Filtrar registros</span><input type="search" id="rel-filtro" placeholder="Filtrar registros…" value="${esc(centralRelatorios.filtro)}"></label></header><div id="rel-tabela"></div></section><section class="rel-metodo"><h2>Como ler este relatório</h2>${r.notas.map(n=>`<p>${esc(n)}</p>`).join('') || '<p>Registros apresentados conforme as fontes locais. Valores ausentes aparecem como —.</p>'}<h3>Fontes</h3>${r.fontes.map(f=>`<code>${esc(f)}</code>`).join('')}${r.escopo==='atual'?'<p>A seleção de data afeta as análises de desempenho. Este relatório operacional mostra o estado atual.</p>':''}</section>`;
  desenhaTabelaRelatorio();
}
function linhasRelatorio() {
  const r=relAtual(), busca=relNormaliza(centralRelatorios.filtro);
  let rows=r.linhas.filter(p=>!busca || r.colunas.some(c=>relNormaliza(relTexto(p[c.key])).includes(busca)));
  const chave=centralRelatorios.ordem;
  if (chave) rows=rows.slice().sort((a,b)=>{
    if (a[chave]==null) return b[chave]==null?0:1;
    if (b[chave]==null) return -1;
    return (relNumero(a[chave]) && relNumero(b[chave]) ? a[chave]-b[chave] : relTexto(a[chave]).localeCompare(relTexto(b[chave]),'pt-BR',{numeric:true}))*centralRelatorios.sentido;
  });
  return rows;
}
function desenhaTabelaRelatorio(impressao = false) {
  const r=relAtual(), rows=linhasRelatorio(), tamanho=30;
  const paginas=Math.max(1,Math.ceil(rows.length/tamanho)); centralRelatorios.pagina=Math.min(centralRelatorios.pagina,paginas-1);
  const pagina=centralRelatorios.pagina, parte=impressao ? rows : rows.slice(pagina*tamanho,(pagina+1)*tamanho);
  document.getElementById('rel-tabela').innerHTML=rows.length?`<div class="rel-table-scroll" tabindex="0" role="region" aria-label="Tabela de ${esc(r.titulo)}"><table><thead><tr>${r.colunas.map(c=>`<th scope="col" aria-sort="${centralRelatorios.ordem===c.key?(centralRelatorios.sentido===1?'ascending':'descending'):'none'}"><button data-rel-ordem="${esc(c.key)}">${esc(c.label)} ${centralRelatorios.ordem===c.key?(centralRelatorios.sentido===1?'↑':'↓'):'↕'}</button></th>`).join('')}</tr></thead><tbody>${parte.map(p=>`<tr>${r.colunas.map(c=>`<td class="${relNumero(p[c.key])?'rel-numero':''}">${relValor(p[c.key],c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div><div class="rel-paginacao"><span>${pagina*tamanho+1}–${Math.min((pagina+1)*tamanho,rows.length)} de ${rows.length} registros</span><div><button class="botao leve" data-rel-pagina="-1" ${pagina===0?'disabled':''}>Anterior</button><span>${pagina+1} / ${paginas}</span><button class="botao leve" data-rel-pagina="1" ${pagina===paginas-1?'disabled':''}>Próxima</button></div></div>`:`<div class="rel-vazio"><strong>${centralRelatorios.filtro?'Nenhum registro corresponde à busca.':'Nenhum registro nesta base.'}</strong><p>${centralRelatorios.filtro?'Tente outra palavra ou limpe o filtro.':'O relatório está pronto para mostrar os dados quando eles forem registrados. Ausência de registros não é uma medição igual a zero.'}</p></div>`;
}
function exportaRelatorio() {
  const r=relAtual();if (!r) return;
  const celula=v=>{let t=v==null?'':relTexto(v); if (/^[\s]*[=+\-@]/.test(t) && !relNumero(v)) t="'"+t;return '"'+t.replaceAll('"','""')+'"';};
  const csv=[r.colunas.map(c=>celula(c.label)).join(';'),...linhasRelatorio().map(p=>r.colunas.map(c=>celula(p[c.key])).join(';'))].join('\r\n');
  const url=URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=`${r.id}-${centralRelatorios.data}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
document.addEventListener('input',e=>{
  if(e.target.id==='rel-busca'){centralRelatorios.busca=e.target.value;desenhaMenuRelatorios();}
  if(e.target.id==='rel-filtro'){centralRelatorios.filtro=e.target.value;centralRelatorios.pagina=0;desenhaTabelaRelatorio();}
});
document.addEventListener('change',e=>{if(e.target.id==='rel-data'){centralRelatorios.data=e.target.value;centralRelatorios.pagina=0;carregaRelatorios(true);}});
document.addEventListener('click',e=>{
  const b=e.target.closest('button');if(!b)return;const d=b.dataset;
  if(d.relId){centralRelatorios.id=d.relId;centralRelatorios.filtro='';centralRelatorios.ordem=null;centralRelatorios.pagina=0;desenhaMenuRelatorios();desenhaDocumentoRelatorio();document.querySelector('.rel-conteudo').scrollTop=0;}
  if(d.relOrdem){centralRelatorios.sentido=centralRelatorios.ordem===d.relOrdem?-centralRelatorios.sentido:1;centralRelatorios.ordem=d.relOrdem;desenhaTabelaRelatorio();}
  if(d.relPagina){centralRelatorios.pagina+=Number(d.relPagina);desenhaTabelaRelatorio();}
  if(d.relAtualizar)carregaRelatorios(true);
  if(d.relCsv)exportaRelatorio();
  if(d.relImprimir)window.print();
});

window.addEventListener('beforeprint',()=>{if(estado.aba==='relatorios' && relAtual())desenhaTabelaRelatorio(true);});
window.addEventListener('afterprint',()=>{if(estado.aba==='relatorios' && relAtual())desenhaTabelaRelatorio();});
