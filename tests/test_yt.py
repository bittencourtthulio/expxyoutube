"""Cliente YouTube: consulta por nome de coluna, cota por dia do Pacífico e erros legíveis."""
import json
from datetime import datetime

import httplib2
import pytest
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

import comum
import yt


class Chamada:
    def __init__(self, resposta):
        self.resposta = resposta

    def execute(self):
        if isinstance(self.resposta, Exception):
            raise self.resposta
        return self.resposta


class Recurso:
    def __init__(self, dono, nome):
        self.dono, self.nome = dono, nome

    def __getattr__(self, metodo):
        def chamar(**kw):
            self.dono.pedidos.append((self.nome, metodo, kw))
            return Chamada(self.dono.respostas[(self.nome, metodo)])
        return chamar


class Servico:
    def __init__(self, respostas):
        self.respostas, self.pedidos = respostas, []

    def __getattr__(self, nome):
        return lambda: Recurso(self, nome)


def http_erro(status, razao, mensagem="erro"):
    corpo = json.dumps({"error": {"code": status, "message": mensagem, "errors": [{"reason": razao}]}}).encode()
    return HttpError(httplib2.Response({"status": status}), corpo)


INSTANTE = datetime(2026, 9, 24, 2, 0, tzinfo=comum.UTC)  # ainda 23/09 no Pacífico


def cliente(tmp_path, data=None, analytics=None):
    return yt.Cliente(data=data or Servico({}), analytics=analytics or Servico({}), raiz=tmp_path, relogio=lambda: INSTANTE)


def test_relatorio_devolve_linhas_por_nome_de_coluna_e_conta_cota(tmp_path):
    analytics = Servico({("reports", "query"): {
        "columnHeaders": [{"name": "day"}, {"name": "views"}, {"name": "likes"}],
        "rows": [["2026-09-20", 10, 1], ["2026-09-21", 12, 0]]}})
    c = cliente(tmp_path, analytics=analytics)
    linhas = c.relatorio("2026-09-01", "2026-09-21", ["views", "likes"], dimensoes=["day"], sort="day")
    assert linhas == [{"day": "2026-09-20", "views": 10, "likes": 1}, {"day": "2026-09-21", "views": 12, "likes": 0}]
    _, _, kw = analytics.pedidos[0]
    assert kw["ids"] == "channel==MINE" and kw["metrics"] == "views,likes" and kw["dimensions"] == "day"
    assert kw["startDate"] == "2026-09-01" and kw["endDate"] == "2026-09-21" and kw["sort"] == "day"
    assert comum.ler_json(tmp_path / "estado" / "cota.json") == {"2026-09-23": {"analytics": 1}}


def test_relatorio_sem_rows_vira_lista_vazia(tmp_path):
    analytics = Servico({("reports", "query"): {"columnHeaders": [{"name": "views"}]}})
    assert cliente(tmp_path, analytics=analytics).relatorio("2026-09-01", "2026-09-02", ["views"]) == []


def test_canal_e_videos_contam_cota_da_data_api(tmp_path):
    data = Servico({
        ("channels", "list"): {"items": [{"id": "UC1", "snippet": {"title": "Canal"}, "statistics": {"subscriberCount": "10"}}]},
        ("videos", "list"): {"items": [{"id": "v1"}, {"id": "v2"}]},
    })
    c = cliente(tmp_path, data=data)
    assert c.canal()["id"] == "UC1"
    assert [v["id"] for v in c.videos(["v1", "v2"])] == ["v1", "v2"]
    assert comum.ler_json(tmp_path / "estado" / "cota.json") == {"2026-09-23": {"data": 2}}
    assert data.pedidos[0][2]["mine"] is True


def test_videos_em_lotes_de_50(tmp_path):
    data = Servico({("videos", "list"): {"items": []}})
    cliente(tmp_path, data=data).videos([f"v{i}" for i in range(120)])
    assert [len(p[2]["id"].split(",")) for p in data.pedidos] == [50, 50, 20]


def test_invalid_grant_vira_erro_auth_com_instrucao(tmp_path):
    analytics = Servico({("reports", "query"): RefreshError("invalid_grant: Token has been expired or revoked.")})
    with pytest.raises(yt.ErroAuth, match="auth.py principal"):
        cliente(tmp_path, analytics=analytics).relatorio("2026-09-01", "2026-09-02", ["views"])


def test_api_desabilitada_vira_erro_api_com_razao(tmp_path):
    analytics = Servico({("reports", "query"): http_erro(403, "accessNotConfigured", "YouTube Analytics API has not been used")})
    with pytest.raises(yt.ErroAPI) as e:
        cliente(tmp_path, analytics=analytics).relatorio("2026-09-01", "2026-09-02", ["views"])
    assert e.value.status == 403 and e.value.razao == "accessNotConfigured"
    assert "habilit" in str(e.value).lower()


def test_401_vira_erro_auth(tmp_path):
    data = Servico({("channels", "list"): http_erro(401, "authError")})
    with pytest.raises(yt.ErroAuth):
        cliente(tmp_path, data=data).canal()


def test_conectar_sem_token_explica(tmp_path):
    with pytest.raises(yt.ErroAuth, match="auth.py principal"):
        yt.Cliente.conectar("principal", raiz=tmp_path)
