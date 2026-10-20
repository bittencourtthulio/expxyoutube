"""Central de relatórios do canal. Somente leitura: não coleta nem publica nada.

Cada relatório segue o mesmo contrato: {id, categoria, titulo, descricao, colunas, linhas, grafico,
notas, textos, kpis, fontes, escopo, coletado_em, data_base}. As linhas saem projetadas nas colunas:
nada fora delas vaza. Ausência nunca vira zero; zero devolvido pela API é preservado.
"""
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from statistics import median

import comum
import dashboard

DIAS_DA_SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def numero(v):
    return comum.numero(v, sinal=True)


def mediana(vs):
    vs = [v for v in vs if numero(v)]
    return round(median(vs), 2) if vs else None


def montar(raiz, data=None, fios=None):
    raiz = Path(raiz)
    avisos = []

    def ler(rel, padrao=None):
        p = raiz / rel
        if not p.exists():
            return {} if padrao is None else padrao
        v = comum.ler_json(p)
        if v is None:
            avisos.append(f"Não foi possível ler {rel}.")
            return {} if padrao is None else padrao
        return v

    def log(rel):
        evs, ruins = comum.ler_jsonl(raiz / rel)
        if ruins:
            avisos.append(f"{ruins} registro(s) inválido(s) ignorado(s) em {rel}.")
        return evs

    pastas = sorted(p.parent.name for p in (raiz / "editorial/analises/relatorios").glob("????-??-??/diagnostico.json"))
    datas = sorted(pastas, reverse=True)
    if data is not None and data not in datas:
        raise ValueError("Data de análise não encontrada.")
    alvo = data or (datas[0] if datas else comum.hoje_sp())
    dia = max((d for d in pastas if d <= alvo), default=None)
    fonte_diag = f"editorial/analises/relatorios/{dia}/diagnostico.json" if dia else ""
    fonte_leitura = f"editorial/analises/relatorios/{dia}/leitura.json" if dia else ""
    diag = ler(fonte_diag) if dia else {}
    leitura = ler(fonte_leitura) if dia else {}
    retrato = {}
    rel_retrato = diag.get("retrato") or ""
    base_dados = (raiz / "editorial/analises/dados").resolve()
    alvo_retrato = (raiz / rel_retrato).resolve() if rel_retrato else None
    if alvo_retrato and base_dados in alvo_retrato.parents and alvo_retrato.suffix == ".json":
        retrato = ler(rel_retrato)
    k = diag.get("kpis") or {}
    videos = diag.get("videos") or []
    tendencia = diag.get("tendencia") or []
    painel = dashboard.montar(diag)
    resultado = []

    def add(ident, categoria, titulo, descricao, colunas, linhas, fonte, grafico=None, notas=None, textos=None, kpis=None, escopo="analise"):
        fontes = [s for s in (fonte if isinstance(fonte, list) else [fonte]) if s]
        da_analise = any(f in (fonte_diag, fonte_leitura, rel_retrato) for f in fontes if f)
        resultado.append({
            "id": ident, "categoria": categoria, "titulo": titulo, "descricao": descricao,
            "colunas": [{"key": c[0], "label": c[1], "formato": c[2] if len(c) > 2 else ""} for c in colunas],
            "linhas": [{c[0]: linha.get(c[0]) for c in colunas} for linha in linhas],
            "grafico": grafico, "notas": notas or [], "textos": [t for t in (textos or []) if t], "kpis": kpis or [],
            "fontes": fontes or ["editorial/analises/relatorios/"], "escopo": escopo,
            "coletado_em": diag.get("coletado_em") if da_analise else None,
            "data_base": dia if da_analise else alvo,
        })

    def chart(x, y, tipo="barras", titulo=None):
        return {"x": x, "y": y, "tipo": tipo, "titulo": titulo}

    def contagens(linhas, chave):
        return [{"nome": str(k_ or "Não informado"), "quantidade": n} for k_, n in Counter(r.get(chave) for r in linhas).most_common()]

    janela = k.get("janela") or {}
    antes = k.get("comparado_com") or {}
    nota_janela = (f"Atual: {janela.get('desde', '—')} a {janela.get('ate', '—')}; anterior: {antes.get('desde', '—')} a "
                   f"{antes.get('ate', '—')}. Fim exclusivo, dias no fuso do Pacífico (o dia da YouTube Analytics).")
    amostra = f"{len(videos)} vídeos com métricas na janela de 28 dias. Métricas acumuladas na janela, não desde a publicação."
    cautela = "Comparação descritiva: idade do vídeo, assunto e formato variam. Não demonstra causalidade."

    # ---------- Canal e crescimento ----------
    indicadores = [{"nome": x["nome"], "atual": x.get("valor"), "anterior": x.get("anterior"), "variacao": x.get("variacao_pct"),
                    "unidade": x.get("unidade")} for x in (k.get("basicas") or []) + (k.get("performance") or [])]
    add("visao-geral", "Canal e crescimento", "Visão geral do canal", "Os KPIs da semana com a semana anterior ao lado.",
        [("nome", "Indicador"), ("atual", "Atual"), ("anterior", "Anterior"), ("variacao", "Variação", "percentual"), ("unidade", "Unidade")],
        indicadores, fonte_diag, notas=[nota_janela], textos=[leitura.get("tese"), leitura.get("subtese")])
    add("views-diarias", "Canal e crescimento", "Views por dia", "Evolução diária de views do canal.",
        [("dia", "Dia"), ("views", "Views")], [t for t in tendencia if numero(t.get("views"))], fonte_diag,
        chart("dia", "views", "linha"), notas=["Dias ausentes são lacunas, nunca zero."])
    add("inscritos-diarios", "Canal e crescimento", "Inscrições por dia", "Inscritos ganhos e inscrições canceladas por dia.",
        [("dia", "Dia"), ("inscritos_ganhos", "Ganhos"), ("inscritos_perdidos", "Cancelados")],
        [t for t in tendencia if numero(t.get("inscritos_ganhos"))], fonte_diag, chart("dia", "inscritos_ganhos", "linha"))
    add("tempo-assistido-diario", "Canal e crescimento", "Minutos assistidos por dia", "Tempo total assistido no canal por dia.",
        [("dia", "Dia"), ("minutos", "Minutos")], [t for t in tendencia if numero(t.get("minutos"))], fonte_diag, chart("dia", "minutos", "linha"))
    add("semanas", "Canal e crescimento", "Quatro semanas", "Views e inscritos ganhos somados por semana.",
        [("desde", "Início"), ("ate", "Fim (exclusivo)"), ("views", "Views"), ("views_dias", "Dias com views"),
         ("inscritos_ganhos", "Inscritos ganhos"), ("inscritos_ganhos_dias", "Dias com inscritos")],
        painel["semanas"], fonte_diag, chart("desde", "views"), notas=["Semana com dia faltando fica sem valor."])
    add("interacoes-semana", "Canal e crescimento", "Interações da semana", "Curtidas, comentários, compartilhamentos e inscrições: atual e anterior.",
        [("nome", "Interação"), ("atual", "Semana atual"), ("anterior", "Semana anterior")], painel["interacoes"], fonte_diag,
        chart("nome", "atual"), notas=[nota_janela])
    t30 = k.get("trinta_dias") or {}
    nomes30 = {"views": "Views", "horas_assistidas": "Horas assistidas", "inscritos_ganhos": "Inscritos ganhos",
               "saldo_inscritos": "Saldo de inscritos", "interacoes": "Interações"}
    add("panorama-30-dias", "Canal e crescimento", "Panorama de 30 dias", "Totais da janela de 30 dias.",
        [("nome", "Indicador"), ("valor", "30 dias")], [{"nome": nomes30[c], "valor": t30.get(c)} for c in nomes30 if c in t30], fonte_diag)

    # ---------- Conteúdo ----------
    colunas_video = [("titulo", "Vídeo"), ("formato", "Formato"), ("publicado_em", "Publicado em"), ("views", "Views"),
                     ("minutos", "Minutos"), ("pct_assistido", "% assistido"), ("taxa_engajamento", "Engajamento", "percentual"),
                     ("inscritos", "Inscritos"), ("nota", "Nota"), ("link", "Abrir", "link")]
    for ident, campo, titulo in [("ranking-views", "views", "Vídeos por views"), ("ranking-tempo", "minutos", "Vídeos por tempo assistido"),
                                 ("ranking-retencao", "pct_assistido", "Vídeos por percentual assistido"),
                                 ("ranking-engajamento", "taxa_engajamento", "Vídeos por engajamento"),
                                 ("ranking-inscritos", "inscritos", "Vídeos que mais trouxeram inscritos"),
                                 ("ranking-comentarios", "comentarios", "Vídeos por comentários")]:
        cols = colunas_video if campo in {c[0] for c in colunas_video} else colunas_video[:3] + [(campo, "Comentários")] + colunas_video[3:]
        ordenados = sorted([v for v in videos if numero(v.get(campo))], key=lambda v: -v[campo])
        add(ident, "Conteúdo", titulo, f"Ranking dos vídeos da janela de 28 dias por {titulo.split(' por ')[-1].lower()}.",
            cols, ordenados, fonte_diag, chart("titulo", campo), notas=[amostra, cautela, "Vídeo sem a métrica fica fora do ranking."])
    add("notas-videos", "Conteúdo", "Nota dos vídeos", "Nota 0 a 10: 5 vezes as views sobre a mediana do mesmo formato (Shorts contra vídeos).",
        [("titulo", "Vídeo"), ("formato", "Formato"), ("views", "Views"), ("mediana_do_formato", "Mediana do formato"), ("nota", "Nota")],
        [v for v in videos if numero(v.get("nota"))], fonte_diag, chart("titulo", "nota"), notas=[amostra, cautela])
    uploads = retrato.get("videos") or []
    add("inventario-uploads", "Conteúdo", "Uploads recentes", "Últimos uploads do canal com números públicos acumulados.",
        [("publicado_em", "Publicado em"), ("titulo", "Vídeo"), ("duracao_seg", "Duração (s)"), ("views_total", "Views totais"),
         ("curtidas_total", "Curtidas"), ("comentarios_total", "Comentários")], uploads, rel_retrato or fonte_diag,
        notas=["Números públicos da Data API, acumulados desde a publicação."])
    dispersao = [v for v in videos if numero(v.get("duracao_seg")) and numero(v.get("pct_assistido"))]
    add("duracao-x-retencao", "Conteúdo", "Duração contra retenção", "Quanto mais longo, menos assistido? Cada ponto é um vídeo.",
        [("titulo", "Vídeo"), ("duracao_seg", "Duração (s)"), ("pct_assistido", "% assistido")], dispersao, fonte_diag,
        chart("duracao_seg", "pct_assistido", "dispersao"), notas=[cautela])

    # ---------- Formatos e tráfego ----------
    formatos = diag.get("formatos") or {}
    colunas_formato = [("tipo", "Formato"), ("views", "Views"), ("minutos", "Minutos"), ("interacoes", "Interações"),
                       ("taxa_engajamento", "Engajamento", "percentual"), ("inscritos", "Inscritos"), ("inscritos_por_mil_views", "Inscritos por mil views")]
    add("formatos-semana", "Formatos e tráfego", "Shorts contra vídeos na semana", "Desempenho por tipo de conteúdo na janela de 7 dias.",
        colunas_formato, formatos.get("7d") or [], fonte_diag, chart("tipo", "views"), notas=[nota_janela])
    add("formatos-28d", "Formatos e tráfego", "Shorts contra vídeos em 28 dias", "Desempenho por tipo de conteúdo na janela de 28 dias.",
        colunas_formato, formatos.get("28d") or [], fonte_diag, chart("tipo", "views"))
    add("trafego-semana", "Formatos e tráfego", "De onde vêm as views", "Origem do tráfego na semana, com a semana anterior.",
        [("rotulo", "Origem"), ("atual", "Views na semana"), ("anterior", "Semana anterior")], painel["trafego"], fonte_diag,
        chart("rotulo", "atual"), notas=[nota_janela])
    trafego28 = [{**t, "rotulo": dashboard.rotulo_trafego(t.get("tipo"))} for t in (diag.get("trafego") or {}).get("28d") or []]
    add("trafego-28d", "Formatos e tráfego", "Origem do tráfego em 28 dias", "Views e minutos por origem na janela de 28 dias.",
        [("rotulo", "Origem"), ("views", "Views"), ("minutos", "Minutos")], trafego28, fonte_diag, chart("rotulo", "views"))

    # ---------- Publicação ----------
    por_dia = defaultdict(list)
    for u in uploads:
        try:
            por_dia[DIAS_DA_SEMANA[date.fromisoformat(u["publicado_em"]).weekday()]].append(u)
        except (KeyError, TypeError, ValueError):
            continue
    dias_semana = [{"dia": d, "uploads": len(por_dia[d]), "views_mediana": mediana(u.get("views_total") for u in por_dia[d])}
                   for d in DIAS_DA_SEMANA if por_dia[d]]
    add("dias-da-semana", "Publicação", "Dia da semana de publicação", "Uploads e views medianas por dia em que o vídeo saiu.",
        [("dia", "Dia"), ("uploads", "Uploads"), ("views_mediana", "Views medianas")], dias_semana, rel_retrato or fonte_diag,
        chart("dia", "views_mediana"), notas=[cautela, "Views totais acumuladas: vídeo mais antigo teve mais tempo."])
    semanas_pub = Counter()
    for u in uploads:
        try:
            ano, sem, _ = date.fromisoformat(u["publicado_em"]).isocalendar()
            semanas_pub[f"{ano}-S{sem:02d}"] += 1
        except (KeyError, TypeError, ValueError):
            continue
    add("cadencia-publicacao", "Publicação", "Cadência de publicação", "Quantos uploads por semana.",
        [("semana", "Semana"), ("uploads", "Uploads")], [{"semana": s, "uploads": n} for s, n in sorted(semanas_pub.items())],
        rel_retrato or fonte_diag, chart("semana", "uploads", "linha"))

    # ---------- Análises e decisões ----------
    add("achados", "Análises e decisões", "Achados e evidências", "Leitura registrada pelo analista.",
        [("titulo", "Achado"), ("achado", "Leitura"), ("evidencia", "Evidência"), ("muda", "O que muda")],
        [a for a in leitura.get("achados") or [] if isinstance(a, dict)], fonte_leitura,
        textos=[leitura.get("tese"), leitura.get("subtese")], notas=[str(x) for x in leitura.get("limites") or []])
    acoes = [{"acao": a[0], "explicacao": a[1] if len(a) > 1 else ""} for a in leitura.get("acoes") or [] if isinstance(a, list) and a]
    add("acoes", "Análises e decisões", "Ações recomendadas", "O que o analista recomenda fazer.",
        [("acao", "Ação"), ("explicacao", "Por quê")], acoes, fonte_leitura)
    dec = log("estado/decisoes.jsonl")
    add("decisoes", "Análises e decisões", "Diário de decisões", "O que foi decidido, por quê e como desfazer.",
        [("quando", "Registrado em"), ("autor", "Autor"), ("tipo", "Tipo"), ("o_que", "Decisão"), ("por_que", "Motivo"),
         ("evidencia", "Evidência"), ("como_desfazer", "Reversão")], list(reversed(dec)), "estado/decisoes.jsonl", escopo="atual")
    add("decisoes-tipo", "Análises e decisões", "Decisões por tipo", "Distribuição das decisões registradas.",
        [("nome", "Tipo"), ("quantidade", "Registros")], contagens(dec, "tipo"), "estado/decisoes.jsonl", chart("nome", "quantidade"), escopo="atual")
    arquivo = []
    for d in datas:
        dg = ler(f"editorial/analises/relatorios/{d}/diagnostico.json")
        arquivo.append({"dia": d, "gerado": dg.get("gerado_em"), "coleta": dg.get("coletado_em"), "videos": len(dg.get("videos") or []),
                        "leitura": (raiz / f"editorial/analises/relatorios/{d}/leitura.json").exists()})
    add("arquivo-analises", "Análises e decisões", "Arquivo de análises", "Diagnósticos gravados, um por dia.",
        [("dia", "Dia"), ("gerado", "Gerado em"), ("coleta", "Coleta usada"), ("videos", "Vídeos"), ("leitura", "Tem leitura")],
        arquivo, "editorial/analises/relatorios/", escopo="atual")
    planos = sorted((raiz / "planejamento").glob("????-??-??.json"))
    ultimo_plano = ler(str(planos[-1].relative_to(raiz))) if planos else {}
    add("pautas-sugeridas", "Análises e decisões", "Pautas sugeridas no plano", "Ideias da biblioteca que o plano mais recente trouxe.",
        [("titulo", "Pauta"), ("cabe_em", "Cabe em"), ("relevancia", "Relevância"), ("video", "Vídeo de origem"), ("fonte", "Nota")],
        ultimo_plano.get("pautas") or [], str(planos[-1].relative_to(raiz)) if planos else "planejamento/", escopo="atual",
        notas=["Ideia é ponto de partida, nunca roteiro. Fato do vídeo de origem só entra conferido na fonte."])

    # ---------- Tarefas e agentes ----------
    fios = fios or []
    cols_t = [("id", "ID"), ("titulo", "Tarefa"), ("tipo", "Tipo"), ("situacao", "Etapa"), ("para", "Responsável"),
              ("data_inicio", "Início"), ("data_final", "Fim"), ("revisar_em", "Revisão")]
    tf = [{**f, "titulo": f.get("titulo") or (f.get("texto") or "")[:100]} for f in fios]
    add("tarefas", "Tarefas e agentes", "Carteira de tarefas", "Situação atual dos pedidos da daily.", cols_t, tf, "estado/daily.jsonl", escopo="atual")
    add("tarefas-estados", "Tarefas e agentes", "Distribuição do kanban", "Quantidade de tarefas em cada etapa.",
        [("nome", "Etapa"), ("quantidade", "Tarefas")], contagens(tf, "situacao"), "estado/daily.jsonl", chart("nome", "quantidade"), escopo="atual")
    add("tarefas-espera", "Tarefas e agentes", "Decisões aguardando você", "Fios que dependem da sua resposta.",
        cols_t + [("texto", "Pedido")], [f for f in tf if f.get("aguarda_usuario")], "estado/daily.jsonl", escopo="atual")
    add("tarefas-agentes", "Tarefas e agentes", "Carga por responsável", "Itens abertos por destinatário.",
        [("nome", "Responsável"), ("quantidade", "Tarefas abertas")], contagens([f for f in tf if f.get("situacao") != "finalizado"], "para"),
        "estado/daily.jsonl", chart("nome", "quantidade"), escopo="atual")
    add("regras-vigentes", "Tarefas e agentes", "Regras e aprendizados em vigor", "Orientações da daily que continuam valendo.",
        [("id", "ID"), ("tipo", "Tipo"), ("texto", "Orientação"), ("serie", "Recorte"), ("onde", "Onde foi aplicada")],
        [f for f in tf if f.get("regra_em_vigor")], "estado/daily.jsonl", escopo="atual")

    # ---------- Conhecimento ----------
    for base, titulo in [("cerebro", "Cérebro de boas práticas"), ("biblioteca", "Biblioteca de pautas")]:
        estado = ler(f"estado/{base}.json").get("canais", {}) if isinstance(ler(f"estado/{base}.json"), dict) else {}
        linhas = [{"nome": nome, "notas": len(list((raiz / base / "videos" / nome).glob("*.md"))), "varredura": c.get("ultima_varredura"),
                   "ultimo": (c.get("ultimo_video") or {}).get("titulo"), "aguardando": len(c.get("aguardando") or {}),
                   "descartados": len(c.get("descartados") or {})} for nome, c in estado.items()]
        add(f"{base}-canais", "Conhecimento", titulo, "Canais, notas locais e estado da ingestão.",
            [("nome", "Canal"), ("notas", "Notas"), ("varredura", "Última varredura"), ("ultimo", "Último vídeo visto"),
             ("aguardando", "Na fila"), ("descartados", "Descartados")], linhas, [f"estado/{base}.json", f"{base}/videos/"],
            chart("nome", "notas"), escopo="atual")

    # ---------- Qualidade dos dados ----------
    add("metricas-recusadas", "Qualidade dos dados", "Métricas recusadas pela API", "Métricas que a API recusou nesta coleta.",
        [("metrica", "Métrica")], [{"metrica": m} for m in k.get("recusadas") or []], fonte_diag,
        notas=["Métrica recusada fica sem valor no painel; nunca vira zero."])
    series = (k.get("series") or {})
    cobertura = [{"serie": nome, "dias": sum(1 for p in pontos if numero(p.get("valor"))), "primeiro": pontos[0]["dia"] if pontos else None,
                  "ultimo": pontos[-1]["dia"] if pontos else None} for nome, pontos in series.items()]
    add("cobertura-series", "Qualidade dos dados", "Cobertura das séries diárias", "Quantos dias cada série trouxe.",
        [("serie", "Série"), ("dias", "Dias com valor"), ("primeiro", "Primeiro dia"), ("ultimo", "Último dia")], cobertura, fonte_diag,
        notas=["A Analytics atrasa de 48 a 72 horas: o último dia é o último processado."])
    cota = ler("estado/cota.json")
    linhas_cota = [{"dia": d, "data": v.get("data"), "analytics": v.get("analytics")} for d, v in sorted(cota.items(), reverse=True)] if isinstance(cota, dict) else []
    add("cota-api", "Qualidade dos dados", "Uso da cota da API", "Chamadas por dia do Pacífico (a cota zera à meia-noite de lá).",
        [("dia", "Dia (Pacífico)"), ("data", "Data API (unidades)"), ("analytics", "Analytics (consultas)")], linhas_cota,
        "estado/cota.json", escopo="atual", notas=["Cota padrão da Data API: 10.000 unidades por dia no projeto inteiro."])

    return {"gerado_em": comum.agora_iso(), "data": alvo, "datas": datas, "coletado_em": diag.get("coletado_em"),
            "diagnostico_em": dia, "avisos": list(dict.fromkeys(avisos)), "relatorios": resultado}
