"""Cliente do YouTube: Data API v3 + Analytics API v2 atrás de uma interface só.

Os serviços são injetáveis (os testes passam um falso), o token é aberto pelo apelido do canal
(nunca pelo caminho na linha de comando) e cada chamada soma cota em `estado/cota.json`,
no dia do Pacífico, que é quando a cota da Google zera.
"""
import json
from datetime import datetime
from pathlib import Path

import comum

RAIZ = Path(__file__).resolve().parent
REFAZER_LOGIN = "refaça o login: .venv/bin/python auth.py principal"
LOTE_VIDEOS = 50


class ErroAuth(RuntimeError):
    """Token ausente, expirado ou revogado."""


class ErroAPI(RuntimeError):
    def __init__(self, status, razao, mensagem):
        self.status, self.razao, self.mensagem = status, razao, mensagem
        dica = ""
        if razao == "accessNotConfigured":
            dica = " Habilite a API no console do Google Cloud do projeto da credencial."
        elif razao in ("quotaExceeded", "dailyLimitExceeded"):
            dica = " A cota do dia acabou; ela zera à meia-noite do Pacífico."
        super().__init__(f"YouTube respondeu {status} ({razao}): {mensagem}.{dica}")


def _traduz(erro):
    from google.auth.exceptions import RefreshError
    from googleapiclient.errors import HttpError

    if isinstance(erro, RefreshError):
        return ErroAuth(f"credencial expirada ou revogada ({erro}); {REFAZER_LOGIN}")
    if isinstance(erro, HttpError):
        status = int(getattr(erro.resp, "status", 0) or 0)
        razao, mensagem = "desconhecida", str(erro)
        try:
            corpo = json.loads(erro.content.decode("utf-8"))["error"]
            mensagem = corpo.get("message", mensagem)
            razao = (corpo.get("errors") or [{}])[0].get("reason", razao)
        except (ValueError, KeyError, AttributeError, IndexError):
            pass
        if status == 401:
            return ErroAuth(f"YouTube recusou a credencial ({mensagem}); {REFAZER_LOGIN}")
        return ErroAPI(status, razao, mensagem)
    return None


class Cliente:
    def __init__(self, data, analytics, raiz=RAIZ, relogio=None):
        self.data, self.analytics, self.raiz = data, analytics, Path(raiz)
        self.relogio = relogio or (lambda: datetime.now(comum.UTC))

    @classmethod
    def conectar(cls, apelido="principal", raiz=RAIZ):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        token = Path(raiz) / "tokens" / f"{apelido}.json"
        if not token.exists():
            raise ErroAuth(f"não há token para '{apelido}'; {REFAZER_LOGIN.replace('principal', apelido)}")
        creds = Credentials.from_authorized_user_file(str(token))
        if not creds.valid:
            try:
                creds.refresh(Request())
            except Exception as e:  # noqa: BLE001 - traduzido abaixo
                raise (_traduz(e) or e) from e
            token.write_text(creds.to_json())
            token.chmod(0o600)
        data = build("youtube", "v3", credentials=creds, cache_discovery=False)
        analytics = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
        return cls(data, analytics, raiz=raiz)

    # ---------- cota ----------

    def _conta(self, bucket, unidades=1):
        arq = self.raiz / "estado" / "cota.json"
        dia = comum.hoje_pacifico(self.relogio())
        cota = comum.ler_json(arq, {}) or {}
        cota = {d: v for d, v in cota.items() if d >= dia[:8] + "01" or d == dia}  # guarda o mês corrente
        cota.setdefault(dia, {})
        cota[dia][bucket] = cota[dia].get(bucket, 0) + unidades
        comum.gravar_json(arq, cota)

    def _executa(self, bucket, pedido, unidades=1):
        try:
            resposta = pedido.execute()
        except Exception as e:  # noqa: BLE001
            traduzido = _traduz(e)
            if traduzido is None:
                raise
            raise traduzido from e
        finally:
            self._conta(bucket, unidades)
        return resposta

    # ---------- Analytics ----------

    def relatorio(self, inicio, fim, metricas, dimensoes=None, filtros=None, sort=None, max_results=None):
        """Linhas de reports.query como dicts pelo nome da coluna. Sem dado = []."""
        kw = {"ids": "channel==MINE", "startDate": inicio, "endDate": fim, "metrics": ",".join(metricas)}
        if dimensoes:
            kw["dimensions"] = ",".join(dimensoes)
        if filtros:
            kw["filters"] = filtros
        if sort:
            kw["sort"] = sort
        if max_results:
            kw["maxResults"] = max_results
        resposta = self._executa("analytics", self.analytics.reports().query(**kw))
        nomes = [c["name"] for c in resposta.get("columnHeaders", [])]
        return [dict(zip(nomes, linha)) for linha in resposta.get("rows") or []]

    # ---------- Data API ----------

    def canal(self):
        resposta = self._executa("data", self.data.channels().list(part="snippet,statistics,contentDetails", mine=True))
        itens = resposta.get("items") or []
        if not itens:
            raise ErroAPI(404, "semCanal", "a credencial não tem canal")
        return itens[0]

    def videos(self, ids):
        saida = []
        ids = list(ids)
        for i in range(0, len(ids), LOTE_VIDEOS):
            lote = ids[i:i + LOTE_VIDEOS]
            resposta = self._executa("data", self.data.videos().list(part="snippet,statistics,contentDetails", id=",".join(lote), maxResults=LOTE_VIDEOS))
            saida.extend(resposta.get("items") or [])
        return saida

    def uploads(self, playlist_id, limite=50):
        """Vídeos da playlist de uploads, do mais novo para o mais antigo."""
        itens, pagina = [], None
        while len(itens) < limite:
            kw = {"part": "contentDetails,snippet", "playlistId": playlist_id, "maxResults": min(50, limite - len(itens))}
            if pagina:
                kw["pageToken"] = pagina
            resposta = self._executa("data", self.data.playlistItems().list(**kw))
            itens.extend(resposta.get("items") or [])
            pagina = resposta.get("nextPageToken")
            if not pagina:
                break
        return itens
