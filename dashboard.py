"""Recortes do painel de análise, derivados do diagnóstico que gerou os KPIs.

Regras: dia ausente é lacuna, nunca zero; a semana só tem valor com os 7 dias medidos
(views e inscritos ganhos são contagens, então a semana é a soma dos dias).
"""
import re
from datetime import date, timedelta

import comum

TRAFEGO = {
    "YT_SEARCH": "Busca do YouTube", "RELATED_VIDEO": "Vídeos sugeridos", "SUBSCRIBER": "Página inicial e inscrições",
    "SHORTS": "Feed de Shorts", "EXT_URL": "Sites externos e Google", "YT_CHANNEL": "Página do canal",
    "YT_OTHER_PAGE": "Outras páginas do YouTube", "PLAYLIST": "Playlists", "NOTIFICATION": "Notificações",
    "NO_LINK_OTHER": "Direto ou desconhecido", "NO_LINK_EMBEDDED": "Player incorporado", "END_SCREEN": "Telas finais",
    "ANNOTATION": "Cards e anotações", "HASHTAGS": "Hashtags", "ADVERTISING": "Anúncios", "PROMOTED": "Promoção",
    "LIVE_REDIRECT": "Redirecionamento de live", "PRODUCT_PAGE": "Página de produto", "SOUND_PAGE": "Página de áudio",
    "VIDEO_REMIXES": "Remixes", "WATCH_WITH": "Assistir junto", "CAMPAIGN_CARD": "Card de campanha",
}
FORMATOS = {"SHORTS": "Shorts", "VIDEO_ON_DEMAND": "Vídeos", "LIVE_STREAM": "Lives", "STORY": "Stories", "UNSPECIFIED": "Sem tipo"}
INTERACOES = ("curtidas", "comentarios", "compartilhamentos", "inscritos_ganhos", "inscritos_perdidos")
LINK_YOUTUBE = re.compile(r"^https://(www\.)?(youtube\.com|youtu\.be)/")
TOP = 10


def rotulo_trafego(tipo):
    return TRAFEGO.get(tipo, f"Outra origem ({tipo})")


def _semanas(k):
    try:
        fim = date.fromisoformat((k.get("janela") or {}).get("ate") or "")
    except ValueError:
        return []
    series = k.get("series") or {}
    mapas = {nome: {p["dia"]: p.get("valor") for p in series.get(nome) or [] if p.get("dia")} for nome in ("views", "inscritos_ganhos")}
    semanas = []
    for i in range(3, -1, -1):
        ate = fim - timedelta(days=7 * i)
        desde = ate - timedelta(days=7)
        dias = [(desde + timedelta(days=n)).isoformat() for n in range(7)]
        s = {"desde": desde.isoformat(), "ate": ate.isoformat(), "dias_esperados": 7}
        for nome, mapa in mapas.items():
            validos = [mapa[d] for d in dias if comum.numero(mapa.get(d))]
            s[nome] = sum(validos) if len(validos) == 7 else None
            s[nome + "_dias"] = len(validos)
        semanas.append(s)
    return semanas


def montar(diagnostico):
    k = (diagnostico or {}).get("kpis") or {}
    kpis = {x["id"]: x for x in (k.get("basicas") or []) + (k.get("performance") or [])}
    interacoes = [{"id": i, "nome": kpis[i]["nome"], "atual": comum.valor(kpis[i].get("valor")), "anterior": comum.valor(kpis[i].get("anterior"))}
                  for i in INTERACOES if i in kpis]

    trafego_bruto = (diagnostico or {}).get("trafego") or {}
    antes = {t["tipo"]: t.get("views") for t in trafego_bruto.get("7d_anteriores") or []}
    trafego = [{"tipo": t["tipo"], "rotulo": rotulo_trafego(t["tipo"]), "atual": comum.valor(t.get("views")),
                "anterior": comum.valor(antes.get(t["tipo"]))} for t in trafego_bruto.get("7d") or []]
    trafego.sort(key=lambda t: -(t["atual"] or 0))

    formatos_bruto = (diagnostico or {}).get("formatos") or {}
    antes = {f["tipo"]: f.get("views") for f in formatos_bruto.get("7d_anteriores") or []}
    formatos = [{"tipo": f["tipo"], "rotulo": FORMATOS.get(f["tipo"], f["tipo"]), "views": comum.valor(f.get("views")),
                 "views_anterior": comum.valor(antes.get(f["tipo"])), "minutos": comum.valor(f.get("minutos")),
                 "taxa_engajamento": comum.valor(f.get("taxa_engajamento")), "inscritos": comum.valor(f.get("inscritos"))}
                for f in formatos_bruto.get("7d") or []]

    top = []
    for v in ((diagnostico or {}).get("videos") or [])[:TOP]:
        item = dict(v)
        item["link"] = v.get("link") if LINK_YOUTUBE.match(v.get("link") or "") else None
        top.append(item)
    return {"semanas": _semanas(k), "interacoes": interacoes, "trafego": trafego, "formatos": formatos, "top_videos": top}
