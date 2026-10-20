"""Falsos do bot do YouTube: HTTP da Bot API, updates de exemplo e binários falsos (claude, yt-dlp, whisper)."""
import json
import os
from pathlib import Path

FIX = Path(__file__).parent / "fixtures" / "bot_youtube"
BIN_FALSO = Path(__file__).parent / "bin_falso"


def updates():
    return json.loads((FIX / "updates.json").read_text(encoding="utf-8"))["result"]


def update(tipo):
    u = next(u for u in updates() if u["_tipo"] == tipo)
    return {k: v for k, v in u.items() if k != "_tipo"}


class HttpFalso:
    """`http(url, dados, arquivos, timeout) -> (status, json)` roteirizado; sem roteiro, responde ok com result True.
    Uma resposta pode ser uma função (metodo, dados) -> json."""

    def __init__(self, *respostas, padrao=None):
        self.respostas = list(respostas)
        self.padrao = padrao
        self.chamadas = []

    def __call__(self, url, dados=None, arquivos=None, timeout=None):
        metodo = url.rsplit("/", 1)[-1]
        self.chamadas.append({"url": url, "metodo": metodo, "dados": dados, "arquivos": arquivos, "timeout": timeout})
        r = self.respostas.pop(0) if self.respostas else (self.padrao or {"ok": True, "result": True})
        if callable(r):
            r = r(metodo, dados or {})
        return (200 if r.get("ok") else r.get("error_code", 400)), r

    def metodos(self):
        return [c["metodo"] for c in self.chamadas]


def roteiro_bin(pasta, nome, **passo):
    """Grava/estende o roteiro dos binários falsos em `pasta` e devolve o ambiente com eles no PATH."""
    pasta = Path(pasta)
    arq = pasta / "roteiro.json"
    roteiro = json.loads(arq.read_text()) if arq.exists() else {}
    roteiro[nome] = passo
    arq.write_text(json.dumps(roteiro))
    env = dict(os.environ)
    env["PATH"] = f"{BIN_FALSO}:{env.get('PATH', '')}"
    env["FALSO_ROTEIRO"] = str(arq)
    env["FALSO_LOG"] = str(pasta / "chamadas.jsonl")
    return env


def chamadas_bin(pasta):
    arq = Path(pasta) / "chamadas.jsonl"
    return [json.loads(l) for l in arq.read_text().splitlines()] if arq.exists() else []


# --- YouTube Data API falso (canal) ---------------------------------------------------------------

class _Req:
    def __init__(self, fn):
        self.fn = fn

    def execute(self):
        return self.fn()


class _Rec:
    def __init__(self, metodos):
        self.metodos = metodos

    def __getattr__(self, nome):
        return lambda **kw: _Req(lambda: self.metodos[nome](**kw))


class CanalFalso:
    """channels/playlistItems/videos/playlists com paginação de 1 item por página nos uploads.
    `videos` = {id: status}; `atualizacoes` guarda os videos.update."""

    def __init__(self, videos=None, playlists=None, canal_id="UC_EXEMPLO_CONFIGURE_O_SEU", erro=None):
        self.videos = videos or {}
        self.lista_playlists = playlists or []
        self.canal_id = canal_id
        self.erro = erro
        self.atualizacoes = []
        self.pedidos = []

    def _checa(self):
        if self.erro:
            raise self.erro

    def _canais(self, part, mine=True):
        self._checa()
        return {"items": [{"id": self.canal_id, "snippet": {"title": "Seu Canal"},
                           "contentDetails": {"relatedPlaylists": {"uploads": "UUuploads"}}}]}

    def _uploads(self, part, playlistId, maxResults=50, pageToken=None):
        self._checa()
        ids = list(self.videos)
        i = int(pageToken or 0)
        pagina = {"items": [{"contentDetails": {"videoId": ids[i]}}]} if i < len(ids) else {"items": []}
        if i + 1 < len(ids):
            pagina["nextPageToken"] = str(i + 1)
        return pagina

    def _videos_list(self, part, id):
        self._checa()
        self.pedidos.append({"part": part, "id": id})
        return {"items": [{"id": v, "status": dict(self.videos[v])} for v in id.split(",") if v in self.videos]}

    def _videos_update(self, part, body):
        self._checa()
        self.atualizacoes.append({"part": part, "body": body})
        self.videos[body["id"]] = dict(body["status"])
        return body

    def _playlists(self, part, mine=True, maxResults=50, pageToken=None):
        self._checa()
        return {"items": [{"id": p["id"], "snippet": {"title": p["titulo"]}} for p in self.lista_playlists]}

    @property
    def data(self):
        return type("Servico", (), {
            "channels": lambda s: _Rec({"list": self._canais}),
            "playlistItems": lambda s: _Rec({"list": self._uploads}),
            "videos": lambda s: _Rec({"list": self._videos_list, "update": self._videos_update}),
            "playlists": lambda s: _Rec({"list": self._playlists}),
        })()

    def cliente(self, raiz):
        import yt
        return yt.Cliente(self.data, None, raiz=raiz)
