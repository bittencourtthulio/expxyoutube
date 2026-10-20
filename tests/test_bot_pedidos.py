"""bot_youtube.pedidos: log só-acréscimo de eventos dos pedidos."""
import json
import multiprocessing
from datetime import datetime

import pytest

from bot_youtube import pedidos
from comum import SP


@pytest.fixture(autouse=True)
def estado(tmp_path, monkeypatch):
    monkeypatch.setattr(pedidos, "ESTADO", tmp_path / "estado")
    return tmp_path / "estado"


def _grava(pasta, n, rotulo):
    pedidos.ESTADO = pasta
    for i in range(n):
        pedidos.registrar_evento("p1", "progresso", nota=f"{rotulo}-{i}")


def test_dois_processos_gravando_ao_mesmo_tempo_nao_perdem_linha(estado):
    ctx = multiprocessing.get_context("fork")
    ps = [ctx.Process(target=_grava, args=(estado, 50, r)) for r in ("a", "b")]
    [p.start() for p in ps]
    [p.join() for p in ps]
    linhas = pedidos.arquivo().read_text().splitlines()
    assert len(linhas) == 100 and all(json.loads(l)["pedido"] == "p1" for l in linhas)


def test_estado_funde_eventos_e_tem_historico():
    agora = datetime(2026, 9, 28, 15, 0, 0, tzinfo=SP)
    pid = pedidos.novo_pedido(url="https://youtu.be/x", quando=agora, etapa="aguardando_escolha")
    pedidos.registrar_evento(pid, "na_fila", modo="motion")
    pedidos.registrar_evento(pid, "produzindo", avisar=True)
    e = pedidos.estado_pedido(pid)
    assert e["etapa"] == "produzindo" and e["modo"] == "motion" and e["url"] == "https://youtu.be/x"
    assert [h["etapa"] for h in e["historico"]] == ["aguardando_escolha", "na_fila", "produzindo"]
    assert pedidos.pasta_pedido(pid).is_dir()


def test_ids_no_mesmo_segundo_ganham_sufixo():
    agora = datetime(2026, 9, 28, 15, 0, 0, tzinfo=SP)
    a = pedidos.novo_pedido(url="u1", quando=agora)
    b = pedidos.novo_pedido(url="u2", quando=agora)
    c = pedidos.novo_pedido(url="u3", quando=agora)
    assert (a, b, c) == ("y20260928-150000", "y20260928-150000-2", "y20260928-150000-3")


def test_pedidos_na_ordem_de_criacao_e_inexistente_e_none():
    a = pedidos.novo_pedido(url="u1")
    b = pedidos.novo_pedido(url="u2")
    pedidos.registrar_evento(a, "cancelado")
    assert [p["pedido"] for p in pedidos.pedidos()] == [a, b]
    assert pedidos.estado_pedido("nao-existe") is None
