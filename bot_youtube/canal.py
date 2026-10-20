"""O canal do YouTube visto pelo bot: horários já agendados (publishAt), playlists e desagendar.

Usa o yt.Cliente do squad (token por apelido, cota somada em estado/cota.json)."""
from datetime import datetime

from comum import SP
from publicacao import WRITABLE_STATUS


class ErroCanal(RuntimeError):
    pass


def conectar(alias):
    """yt.Cliente do alias. Com BOT_YT_CANAL_FALSO (só em teste de subprocesso), um canal lido de um JSON local."""
    import os

    import yt
    falso = os.environ.get("BOT_YT_CANAL_FALSO")
    if falso:
        return _cliente_json(falso)
    return yt.Cliente.conectar(alias)


def _cliente_json(caminho):
    import json
    from pathlib import Path

    import yt
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))

    class Req:
        def __init__(self, fn):
            self.fn = fn

        def execute(self):
            return self.fn()

    class Rec:
        def __init__(self, metodos):
            self.metodos = metodos

        def __getattr__(self, nome):
            return lambda **kw: Req(lambda: self.metodos[nome](**kw))

    videos = dados.get("videos") or {}

    def atualizar(part, body):
        videos[body["id"]] = body["status"]
        Path(caminho).write_text(json.dumps({**dados, "videos": videos}, ensure_ascii=False), encoding="utf-8")
        return body

    class Servico:
        def channels(self):
            return Rec({"list": lambda **kw: {"items": [{"id": dados["canal_id"], "snippet": {"title": dados.get("titulo", "canal")},
                                                          "contentDetails": {"relatedPlaylists": {"uploads": "UU"}}}]}})

        def playlistItems(self):
            return Rec({"list": lambda **kw: {"items": [{"contentDetails": {"videoId": v}} for v in videos]}})

        def videos(self):
            return Rec({"list": lambda part, id: {"items": [{"id": v, "status": videos[v]} for v in id.split(",") if v in videos]},
                        "update": atualizar})

        def playlists(self):
            return Rec({"list": lambda **kw: {"items": [{"id": p["id"], "snippet": {"title": p["titulo"]}} for p in dados.get("playlists") or []]}})

    return yt.Cliente(Servico(), None, raiz=Path(caminho).parent)


def _paginas(cliente, recurso, **kw):
    itens, token = [], None
    while True:
        consulta = dict(kw, **({"pageToken": token} if token else {}))
        pagina = cliente._executa("data", getattr(cliente.data, recurso)().list(**consulta))
        itens.extend(pagina.get("items") or [])
        token = pagina.get("nextPageToken")
        if not token:
            return itens


def _status(cliente, ids):
    saida = {}
    for i in range(0, len(ids), 50):
        r = cliente._executa("data", cliente.data.videos().list(part="status", id=",".join(ids[i:i + 50])))
        saida.update({v["id"]: v.get("status") or {} for v in r.get("items") or []})
    return saida


def agendados(cliente):
    """publishAt (em America/Sao_Paulo) de todo vídeo privado com agendamento na playlist de uploads, em ordem."""
    canal = cliente._executa("data", cliente.data.channels().list(part="contentDetails", mine=True))["items"][0]
    uploads = canal["contentDetails"]["relatedPlaylists"]["uploads"]
    ids = [i["contentDetails"]["videoId"] for i in _paginas(cliente, "playlistItems", part="contentDetails", playlistId=uploads, maxResults=50)]
    horas = []
    for st in _status(cliente, ids).values():
        if st.get("privacyStatus") == "private" and st.get("publishAt"):
            horas.append(datetime.fromisoformat(st["publishAt"].replace("Z", "+00:00")).astimezone(SP))
    return sorted(horas)


def playlists(cliente):
    return [{"id": p["id"], "titulo": p["snippet"]["title"]} for p in _paginas(cliente, "playlists", part="snippet", mine=True, maxResults=50)]


def desagendar(cliente, video_id):
    """Tira o agendamento: o vídeo fica privado, sem publishAt; os campos de status escrevíveis são preservados."""
    atual = _status(cliente, [video_id]).get(video_id)
    if atual is None:
        raise ErroCanal(f"vídeo {video_id} não está no canal")
    status = {k: atual[k] for k in WRITABLE_STATUS if k in atual}
    status["privacyStatus"] = "private"
    corpo = {"id": video_id, "status": status}
    cliente._executa("data", cliente.data.videos().update(part="status", body=corpo), unidades=50)
    return corpo
