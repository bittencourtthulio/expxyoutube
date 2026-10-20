"""Coleta as métricas do canal na YouTube Analytics API e na Data API (somente leitura).

    .venv/bin/python editorial/analises/coletar_youtube.py [--apelido principal]

Grava o retrato bruto em editorial/analises/dados/youtube/<AAAA-MM-DDTHHMM>_30d.json.
As janelas terminam no último dia que a API já processou (a Analytics tem 48 a 72 h de atraso),
nunca em "ontem": uma janela que termina em dia sem dado ficaria menor que a anterior.
Os dias são do fuso do Pacífico, que é o dia da API. `ate` é exclusivo.
"""
import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import comum  # noqa: E402
import yt  # noqa: E402

DESTINO = RAIZ / "editorial" / "analises" / "dados" / "youtube"
PROCURA_DIAS = 45  # quanto voltar procurando o último dia com dado


class SemDados(RuntimeError):
    pass


def _d(iso):
    return date.fromisoformat(iso)


def _janela(ate, dias):
    return {"desde": (ate - timedelta(days=dias)).isoformat(), "ate": ate.isoformat()}


def janelas(cliente, hoje=None):
    """Janelas 7d, 7d_anteriores, 28d e 30d terminando no último dia com dado (ate exclusivo)."""
    hoje = hoje or comum.hoje_pacifico()
    inicio = (_d(hoje) - timedelta(days=PROCURA_DIAS)).isoformat()
    linhas = cliente.relatorio(inicio, hoje, ["views"], dimensoes=["day"], sort="day")
    if not linhas:
        raise SemDados(f"nenhum dia com dado entre {inicio} e {hoje} na YouTube Analytics")
    ultimo = max(l["day"] for l in linhas)
    ate = _d(ultimo) + timedelta(days=1)
    return {
        "ultimo_dia": ultimo,
        "7d": _janela(ate, 7),
        "7d_anteriores": _janela(ate - timedelta(days=7), 7),
        "28d": _janela(ate, 28),
        "30d": _janela(ate, 30),
    }


METRICAS_JANELA = [
    "views", "engagedViews", "estimatedMinutesWatched", "averageViewDuration", "averageViewPercentage",
    "likes", "dislikes", "comments", "shares", "subscribersGained", "subscribersLost", "videosAddedToPlaylists",
]
# séries diárias: métrica da API -> nome no harness (todas são contagens somáveis)
SERIES = {
    "views": "views", "engagedViews": "engaged_views", "estimatedMinutesWatched": "minutos",
    "subscribersGained": "inscritos_ganhos", "subscribersLost": "inscritos_perdidos",
    "likes": "curtidas", "comments": "comentarios", "shares": "compartilhamentos",
}
DIAS_DE_SERIE = 60


def _fim_inclusivo(janela):
    return (_d(janela["ate"]) - timedelta(days=1)).isoformat()


def _consulta_tolerante(cliente, inicio, fim, metricas, **kw):
    """Pede tudo numa chamada; se a API recusar (400), pede métrica a métrica e registra as recusadas."""
    try:
        return cliente.relatorio(inicio, fim, metricas, **kw), []
    except yt.ErroAPI as e:
        if e.status != 400:
            raise
    linhas_por_metrica, recusadas = {}, []
    for m in metricas:
        try:
            linhas_por_metrica[m] = cliente.relatorio(inicio, fim, [m], **kw)
        except yt.ErroAPI as e:
            if e.status != 400:
                raise
            recusadas.append({"metrica": m, "erro": str(e)[:200]})
    return linhas_por_metrica, recusadas


def _totais(cliente, janela):
    linhas, recusadas = _consulta_tolerante(cliente, janela["desde"], _fim_inclusivo(janela), METRICAS_JANELA)
    valores = {}
    if isinstance(linhas, dict):  # veio métrica a métrica
        for m, ls in linhas.items():
            if ls:
                valores[m] = ls[0][m]
    elif linhas:
        valores = dict(linhas[0])
    return {**janela, "valores": valores, "recusadas": recusadas}


def _series(cliente, ultimo_dia):
    inicio = (_d(ultimo_dia) - timedelta(days=DIAS_DE_SERIE - 1)).isoformat()
    linhas, recusadas = _consulta_tolerante(cliente, inicio, ultimo_dia, list(SERIES), dimensoes=["day"], sort="day")
    series = {}
    if isinstance(linhas, dict):
        for m, ls in linhas.items():
            series[SERIES[m]] = [{"dia": l["day"], "valor": l[m]} for l in ls]
    else:
        for m, nome in SERIES.items():
            series[nome] = [{"dia": l["day"], "valor": l[m]} for l in linhas if m in l]
    return series, recusadas


def coletar_canal(cliente, jan):
    series, recusadas_series = _series(cliente, jan["ultimo_dia"])
    return {
        "ultimo_dia": jan["ultimo_dia"],
        "janelas": {nome: _totais(cliente, jan[nome]) for nome in ("7d", "7d_anteriores", "28d", "30d")},
        "series": series,
        "series_recusadas": recusadas_series,
    }


METRICAS_TOP = ["views", "estimatedMinutesWatched", "averageViewDuration", "averageViewPercentage",
                "likes", "comments", "shares", "subscribersGained"]
NOMES_TOP = {"views": "views", "estimatedMinutesWatched": "minutos", "averageViewDuration": "duracao_media",
             "averageViewPercentage": "pct_assistido", "likes": "curtidas", "comments": "comentarios",
             "shares": "compartilhamentos", "subscribersGained": "inscritos"}
METRICAS_FORMATO = ["views", "estimatedMinutesWatched", "likes", "comments", "shares", "subscribersGained"]
MAX_TOP = 50  # a API aceita até 200; o painel mostra 10 e a nota usa todos
LIMITE_SHORT_SEG = 180  # Shorts têm até 3 minutos; usado só quando a Analytics não diz o formato do vídeo


def _trafego(cliente, janela):
    linhas = cliente.relatorio(janela["desde"], _fim_inclusivo(janela), ["views", "estimatedMinutesWatched"],
                               dimensoes=["insightTrafficSourceType"], sort="-views")
    return [{"tipo": l["insightTrafficSourceType"], "views": l["views"], "minutos": l["estimatedMinutesWatched"]} for l in linhas]


def normaliza_formato(valor):
    """A API real devolve creatorContentType em camelCase (videoOnDemand, shorts); a documentação usa MAIÚSCULAS."""
    import re
    valor = str(valor or "")
    if valor == "creatorContentTypeUnspecified":
        return "UNSPECIFIED"
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", valor).upper()


def _formatos(cliente, janela):
    """creatorContentType só é aceito junto de day no relatório por tempo: pede por dia e soma aqui."""
    linhas = cliente.relatorio(janela["desde"], _fim_inclusivo(janela), METRICAS_FORMATO,
                               dimensoes=["day", "creatorContentType"], sort="day")
    soma = {}
    for l in linhas:
        alvo = soma.setdefault(normaliza_formato(l["creatorContentType"]), {m: 0 for m in METRICAS_FORMATO})
        for m in METRICAS_FORMATO:
            alvo[m] += l.get(m) or 0
    return [{"tipo": t, "views": v["views"], "minutos": v["estimatedMinutesWatched"], "curtidas": v["likes"],
             "comentarios": v["comments"], "compartilhamentos": v["shares"], "inscritos": v["subscribersGained"]}
            for t, v in sorted(soma.items(), key=lambda kv: -kv[1]["views"]) if not (t == "UNSPECIFIED" and not v["views"])]


def _duracao_seg(iso):
    """PT1H2M3S -> 3723. Formato inválido -> None."""
    import re
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m or not any(m.groups()):
        return None
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def _dia_pacifico(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(comum.PACIFICO).date().isoformat()


def _link(vid, formato):
    return f"https://www.youtube.com/shorts/{vid}" if formato == "SHORTS" else f"https://www.youtube.com/watch?v={vid}"


def _top(cliente, janela, detalhes):
    ini, fim = janela["desde"], _fim_inclusivo(janela)
    linhas = cliente.relatorio(ini, fim, METRICAS_TOP, dimensoes=["video"], sort="-views", max_results=MAX_TOP)
    try:
        formato = {l["video"]: normaliza_formato(l["creatorContentType"]) for l in
                   cliente.relatorio(ini, fim, ["views"], dimensoes=["video", "creatorContentType"], sort="-views", max_results=MAX_TOP)}
        formato_por = "analytics"
    except yt.ErroAPI as e:
        if e.status != 400:
            raise
        formato, formato_por = {}, "duracao"  # a API real recusa video+creatorContentType: o formato sai da duração
    faltam = [l["video"] for l in linhas if l["video"] not in detalhes]
    for v in cliente.videos(faltam):
        detalhes[v["id"]] = v
    top = []
    for l in linhas:
        vid = l["video"]
        info = detalhes.get(vid, {})
        duracao = _duracao_seg(info.get("contentDetails", {}).get("duration"))
        if formato_por == "analytics":
            fmt = formato.get(vid, "UNSPECIFIED")
        else:
            fmt = "SHORTS" if duracao is not None and duracao <= LIMITE_SHORT_SEG else "VIDEO_ON_DEMAND"
        item = {"id": vid, "titulo": info.get("snippet", {}).get("title"), "formato": fmt, "formato_por": formato_por, "link": _link(vid, fmt),
                "publicado_em": _dia_pacifico(info["snippet"]["publishedAt"]) if info.get("snippet", {}).get("publishedAt") else None,
                "duracao_seg": _duracao_seg(info.get("contentDetails", {}).get("duration"))}
        item.update({NOMES_TOP[m]: l.get(m) for m in METRICAS_TOP})
        top.append(item)
    return top


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _canal_e_uploads(cliente, jan, limite=50):
    canal = cliente.canal()
    uploads = cliente.uploads(canal["contentDetails"]["relatedPlaylists"]["uploads"], limite=limite)
    detalhes = {v["id"]: v for v in cliente.videos([u["contentDetails"]["videoId"] for u in uploads])}
    videos = []
    for u in uploads:
        v = detalhes.get(u["contentDetails"]["videoId"])
        if not v:
            continue
        st = v.get("statistics", {})
        videos.append({"id": v["id"], "titulo": v["snippet"]["title"], "publicado_em": _dia_pacifico(v["snippet"]["publishedAt"]),
                       "duracao_seg": _duracao_seg(v.get("contentDetails", {}).get("duration")),
                       "views_total": _int(st.get("viewCount")), "curtidas_total": _int(st.get("likeCount")),
                       "comentarios_total": _int(st.get("commentCount"))})
    publicacoes = {nome: sum(1 for v in videos if jan[nome]["desde"] <= v["publicado_em"] < jan[nome]["ate"])
                   for nome in ("7d", "7d_anteriores")}
    st = canal.get("statistics", {})
    info = {"id": canal["id"], "titulo": canal["snippet"].get("title"), "handle": canal["snippet"].get("customUrl"),
            "inscritos": _int(st.get("subscriberCount")), "videos_total": _int(st.get("videoCount")),
            "views_total": _int(st.get("viewCount")), "publicacoes": publicacoes}
    return info, videos, detalhes


def coletar(cliente, hoje=None, agora=None):
    jan = janelas(cliente, hoje)
    canal, videos, detalhes = _canal_e_uploads(cliente, jan)
    retrato = {"coletado_em": (agora or datetime.now(comum.UTC)).isoformat(timespec="seconds"),
               "periodo_dias": 30, "fuso_dos_dias": "America/Los_Angeles", "canal": canal}
    retrato.update(coletar_canal(cliente, jan))
    retrato["trafego"] = {n: _trafego(cliente, jan[n]) for n in ("7d", "7d_anteriores", "28d")}
    retrato["formatos"] = {n: _formatos(cliente, jan[n]) for n in ("7d", "7d_anteriores", "28d")}
    retrato["top_videos"] = _top(cliente, jan["28d"], detalhes)
    retrato["videos"] = videos
    return retrato


def main(argv=None, cliente=None, raiz=None, hoje=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apelido", default="principal", help="token em tokens/<apelido>.json (padrão: principal)")
    args = ap.parse_args(argv)
    raiz = Path(raiz or RAIZ)
    cliente = cliente or yt.Cliente.conectar(args.apelido, raiz=raiz)
    retrato = coletar(cliente, hoje=hoje)
    carimbo = datetime.now(comum.SP).strftime("%Y-%m-%dT%H%M")
    destino = raiz / "editorial" / "analises" / "dados" / "youtube" / f"{carimbo}_30d.json"
    comum.gravar_json(destino, retrato)
    return destino


if __name__ == "__main__":
    try:
        print(main())
    except (yt.ErroAuth, yt.ErroAPI, SemDados) as e:
        sys.exit(f"erro: {e}")
