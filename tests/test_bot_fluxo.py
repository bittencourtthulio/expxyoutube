"""bot_youtube.fluxo: transições do pedido (escolha, aprovar, ajuste, cancelar, refazer) e vencidos para envio."""
from datetime import datetime

import pytest

from bot_youtube import fluxo, pedidos
from comum import SP


@pytest.fixture(autouse=True)
def estado(tmp_path, monkeypatch):
    monkeypatch.setattr(pedidos, "ESTADO", tmp_path / "estado")


def _pronto(horario="2026-09-29T16:00:00-03:00", envio="2026-09-29T15:00:00-03:00"):
    pid = pedidos.novo_pedido(url="u", etapa="aguardando_escolha")
    fluxo.escolher_modo(pid, "motion")
    pedidos.registrar_evento(pid, "aguardando_envio", avisar=True, horario=horario, envio_em=envio)
    return pid


# --- T-02.03 -------------------------------------------------------------------------------------

def test_escolha_e_cancelamento_no_log_real():
    pid = pedidos.novo_pedido(url="u", etapa="aguardando_escolha")
    assert fluxo.escolher_modo(pid, "avatar")[0] is True
    ok, texto = fluxo.cancelar(pid)
    assert ok and pedidos.estado_pedido(pid)["etapa"] == "cancelado"
    assert [h["etapa"] for h in pedidos.estado_pedido(pid)["historico"]] == ["aguardando_escolha", "na_fila", "cancelado"]
    assert pedidos.estado_pedido(pid)["modo"] == "avatar"


def test_escolher_de_novo_recusa_com_a_etapa():
    pid = pedidos.novo_pedido(url="u", etapa="aguardando_escolha")
    fluxo.escolher_modo(pid, "motion")
    ok, texto = fluxo.escolher_modo(pid, "avatar")
    assert not ok and "na_fila" in texto and pedidos.estado_pedido(pid)["modo"] == "motion"


def test_modo_invalido_e_pedido_inexistente():
    pid = pedidos.novo_pedido(url="u", etapa="aguardando_escolha")
    assert fluxo.escolher_modo(pid, "outro")[0] is False
    assert fluxo.escolher_modo("nao-existe", "motion")[0] is False


def test_refazer_so_de_falhou():
    pid = pedidos.novo_pedido(url="u", etapa="aguardando_escolha")
    fluxo.escolher_modo(pid, "motion")
    assert fluxo.refazer(pid)[0] is False
    pedidos.registrar_evento(pid, "falhou", nota="x")
    assert fluxo.refazer(pid)[0] is True and pedidos.estado_pedido(pid)["etapa"] == "na_fila"


def test_cancelado_nao_cancela_de_novo():
    pid = pedidos.novo_pedido(url="u", etapa="aguardando_escolha")
    fluxo.cancelar(pid)
    assert fluxo.cancelar(pid)[0] is False


# --- T-02.04 -------------------------------------------------------------------------------------

def test_pedir_ajuste_e_ajustar_mantem_o_horario():
    pid = _pronto()
    assert fluxo.pedir_ajuste(pid)[0]
    ok, texto = fluxo.ajustar(pid, "trocar o gancho")
    e = pedidos.estado_pedido(pid)
    assert ok and e["etapa"] == "ajuste" and e["ajuste_pendente"] == "trocar o gancho"
    assert e["horario"] == "2026-09-29T16:00:00-03:00" and "trocar o gancho" in texto


def test_aprovar_em_aguardando_ajuste_recusa_sem_evento():
    pid = _pronto()
    fluxo.pedir_ajuste(pid)
    n = len(pedidos.eventos(pid))
    ok, _ = fluxo.aprovar(pid)
    assert not ok and len(pedidos.eventos(pid)) == n


def test_aprovar_poe_envio_agora():
    pid = _pronto()
    agora = datetime(2026, 9, 28, 18, 0, tzinfo=SP)
    ok, texto = fluxo.aprovar(pid, agora=agora)
    e = pedidos.estado_pedido(pid)
    assert ok and e["etapa"] == "aprovado" and e["envio_em"] == agora.isoformat(timespec="seconds") and "29/09 às 16:00" in texto
    assert fluxo.aprovar(pid)[0] is False


def test_manter_volta_a_esperar_envio():
    pid = _pronto()
    fluxo.pedir_ajuste(pid)
    assert fluxo.manter(pid)[0] and pedidos.estado_pedido(pid)["etapa"] == "reagendado"
    assert fluxo.aguardando_ajuste() is None


def test_ajustar_vazio_recusa():
    pid = _pronto()
    assert fluxo.ajustar(pid, "  ")[0] is False


def test_previa_enviada_nao_muda_a_etapa():
    pid = _pronto()
    pedidos.registrar_evento(pid, "previa_enviada", message_id=55)
    e = pedidos.estado_pedido(pid)
    assert e["etapa"] == "aguardando_envio" and e["message_id"] == 55
    assert fluxo.aprovar(pid)[0] is True


# --- T-02.05 -------------------------------------------------------------------------------------

def test_vencidos_aprovado_e_prazo_chegado_mas_nao_ajuste():
    a = _pronto()
    fluxo.aprovar(a, agora=datetime(2026, 9, 28, 10, 0, tzinfo=SP))
    b = _pronto()
    c = _pronto()
    fluxo.pedir_ajuste(c)
    agora = datetime(2026, 9, 29, 15, 0, tzinfo=SP)
    assert [p["pedido"] for p in fluxo.vencidos(agora)] == [a, b]


def test_prazo_ainda_nao_chegou():
    _pronto()
    assert fluxo.vencidos(datetime(2026, 9, 29, 14, 59, tzinfo=SP)) == []
