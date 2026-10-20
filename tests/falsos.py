"""Falso da YouTube Data API v3 + Analytics API v2 para os testes.

Imita a interface encadeada do google-api-python-client (`servico.reports().query(**kw).execute()`)
e responde por dimensão e métricas pedidas, com dados determinísticos:
todo dia com dado tem as mesmas contagens (POR_DIA), de `primeiro_dia` a `ultimo_dia`.
"""
import json
from datetime import date, timedelta

import httplib2
from googleapiclient.errors import HttpError

import yt

POR_DIA = {
    "views": 100, "engagedViews": 90, "estimatedMinutesWatched": 250, "likes": 5, "dislikes": 0,
    "comments": 2, "shares": 1, "subscribersGained": 3, "subscribersLost": 1, "videosAddedToPlaylists": 1,
}
MEDIAS = {"averageViewDuration": 150, "averageViewPercentage": 40.0}
# fatias de views por tipo de tráfego; BROWSE_NOVO simula um valor que a API passou a devolver
TRAFEGO = {"YT_SEARCH": 0.3, "RELATED_VIDEO": 0.25, "SUBSCRIBER": 0.2, "SHORTS": 0.15, "EXT_URL": 0.05, "BROWSE_NOVO": 0.05}
FORMATOS = {"SHORTS": 0.3, "VIDEO_ON_DEMAND": 0.7}
SHORTS = {"v02", "v05", "v08"}


def _dias(inicio, fim):
    d, f = date.fromisoformat(inicio), date.fromisoformat(fim)
    while d <= f:
        yield d.isoformat()
        d += timedelta(days=1)


def _erro(status, razao):
    corpo = json.dumps({"error": {"code": status, "message": razao, "errors": [{"reason": razao}]}}).encode()
    return HttpError(httplib2.Response({"status": status}), corpo)


class _Chamada:
    def __init__(self, fn):
        self.fn = fn

    def execute(self):
        return self.fn()


class _Recurso:
    def __init__(self, metodos):
        self.metodos = metodos

    def __getattr__(self, nome):
        fn = self.metodos[nome]
        return lambda **kw: _Chamada(lambda: fn(**kw))


class _Servico:
    def __init__(self, recursos):
        self.recursos = recursos

    def __getattr__(self, nome):
        return lambda: _Recurso(self.recursos[nome])


class YouTubeFalso:
    def __init__(self, ultimo_dia="2026-09-20", primeiro_dia="2026-06-01", recusar=(), n_videos=12, por_dia=None, recusar_video_formato=False):
        self.ultimo_dia, self.primeiro_dia = ultimo_dia, primeiro_dia
        self.recusar_video_formato = recusar_video_formato
        self.recusar = set(recusar)
        self.por_dia = por_dia or (lambda dia: dict(POR_DIA))
        self.pedidos = []
        self.catalogo = {}
        base = date(2026, 9, 18)
        for i in range(1, n_videos + 1):
            vid = f"v{i:02d}"
            self.catalogo[vid] = {
                "id": vid,
                "snippet": {"title": f"Vídeo {i:02d}", "publishedAt": f"{(base - timedelta(days=5 * i)).isoformat()}T15:00:00Z",
                            "description": f"Descrição {i}", "tags": ["ia"]},
                "statistics": {"viewCount": str(5000 // i), "likeCount": str(100 // i), "commentCount": str(20 // i)},
                "contentDetails": {"duration": "PT45S" if vid in SHORTS else f"PT{8 + i}M"},
            }
        self.analytics = _Servico({"reports": {"query": self._query}})
        self.data = _Servico({
            "channels": {"list": self._canais},
            "videos": {"list": self._videos},
            "playlistItems": {"list": self._uploads},
        })

    def cliente(self, raiz):
        return yt.Cliente(self.data, self.analytics, raiz=raiz)

    # ---------- Analytics ----------

    def _dias_com_dado(self, inicio, fim):
        return [d for d in _dias(inicio, fim) if self.primeiro_dia <= d <= self.ultimo_dia]

    def _query(self, ids, startDate, endDate, metrics, dimensions=None, sort=None, maxResults=None, filters=None):
        self.pedidos.append({"startDate": startDate, "endDate": endDate, "metrics": metrics, "dimensions": dimensions, "sort": sort})
        metricas = metrics.split(",")
        if self.recusar & set(metricas):
            raise _erro(400, "badRequest")
        dias = self._dias_com_dado(startDate, endDate)
        dims = dimensions.split(",") if dimensions else []

        def valores(fatia=1.0, dia_unico=None):
            linha = []
            for m in metricas:
                if m in MEDIAS:
                    linha.append(MEDIAS[m])
                else:
                    total = sum(self.por_dia(d).get(m, 0) for d in ([dia_unico] if dia_unico else dias))
                    linha.append(round(total * fatia))
            return linha

        if not dims:
            rows = [valores()] if dias else []
        elif dims == ["day"]:
            rows = [[d] + valores(dia_unico=d) for d in dias]
        elif dims == ["insightTrafficSourceType"]:
            rows = [[t] + valores(f) for t, f in TRAFEGO.items()] if dias else []
        elif dims == ["creatorContentType"]:
            rows = [[t] + valores(f) for t, f in FORMATOS.items()] if dias else []
        elif dims == ["day", "creatorContentType"]:
            rows = [[d, t] + valores(f, dia_unico=d) for d in dias for t, f in FORMATOS.items()]
        elif dims == ["video", "creatorContentType"] and self.recusar_video_formato:
            raise _erro(400, "badRequest")  # a API real recusa essa combinação (visto em 2026-09-23)
        elif dims in (["video"], ["video", "creatorContentType"]):
            vids = list(self.catalogo)
            pesos = {v: 1 / (i + 1) for i, v in enumerate(vids)}
            soma = sum(pesos.values())
            extra = (lambda v: [v, "SHORTS" if v in SHORTS else "VIDEO_ON_DEMAND"]) if len(dims) == 2 else (lambda v: [v])
            rows = [extra(v) + valores(pesos[v] / soma) for v in vids] if dias else []
        else:
            raise _erro(400, "badRequest")
        if sort:
            chave = sort.lstrip("-")
            if chave in metricas or chave in dims:
                col = len(dims) + metricas.index(chave) if chave in metricas else dims.index(chave)
                rows.sort(key=lambda r: r[col], reverse=sort.startswith("-"))
        if maxResults:
            rows = rows[:maxResults]
        cab = [{"name": d, "columnType": "DIMENSION"} for d in dims] + [{"name": m, "columnType": "METRIC"} for m in metricas]
        resposta = {"kind": "youtubeAnalytics#resultTable", "columnHeaders": cab}
        if rows:
            resposta["rows"] = rows
        return resposta

    # ---------- Data API ----------

    def _canais(self, part, mine=None, id=None):
        return {"items": [{
            "id": "UCfalso",
            "snippet": {"title": "Canal Falso", "customUrl": "@canalfalso"},
            "statistics": {"subscriberCount": "9630", "videoCount": str(len(self.catalogo)), "viewCount": "118360"},
            "contentDetails": {"relatedPlaylists": {"uploads": "UUfalso"}},
        }]}

    def _videos(self, part, id, maxResults=None):
        return {"items": [self.catalogo[v] for v in id.split(",") if v in self.catalogo]}

    def _uploads(self, part, playlistId, maxResults=50, pageToken=None):
        vids = list(self.catalogo)
        inicio = int(pageToken or 0)
        fatia = vids[inicio:inicio + maxResults]
        resposta = {"items": [{"contentDetails": {"videoId": v, "videoPublishedAt": self.catalogo[v]["snippet"]["publishedAt"]},
                               "snippet": {"title": self.catalogo[v]["snippet"]["title"]}} for v in fatia]}
        if inicio + maxResults < len(vids):
            resposta["nextPageToken"] = str(inicio + maxResults)
        return resposta
