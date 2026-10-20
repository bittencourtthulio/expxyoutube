"""bot_youtube.slots: horários tomados e o próximo slot livre de YT_SLOTS."""
from datetime import datetime, timedelta

import pytest

from bot_youtube import pedidos, slots
from comum import SP


@pytest.fixture(autouse=True)
def estado(tmp_path, monkeypatch):
    monkeypatch.setattr(pedidos, "ESTADO", tmp_path / "estado")


def _pedido(etapa, horario):
    pid = pedidos.novo_pedido(url="u", etapa="na_fila")
    pedidos.registrar_evento(pid, etapa, horario=horario)
    return pid


def test_ocupados_une_canal_e_pedidos_ativos():
    _pedido("aguardando_envio", "2026-09-29T16:00:00-03:00")
    canal = [datetime(2026, 9, 29, 10, 0, tzinfo=SP), datetime(2026, 9, 30, 10, 0, tzinfo=SP)]
    assert slots.ocupados("2026-09-29", canal) == ["10:00", "16:00"]


def test_cancelado_nao_ocupa_e_ajuste_ocupa():
    _pedido("cancelado", "2026-09-29T20:00:00-03:00")
    assert slots.ocupados("2026-09-29", []) == []
    _pedido("ajuste", "2026-09-29T20:00:00-03:00")
    assert slots.ocupados("2026-09-29", []) == ["20:00"]


def test_ocupados_ignora_o_proprio_pedido():
    pid = _pedido("aguardando_envio", "2026-09-29T16:00:00-03:00")
    assert slots.ocupados("2026-09-29", [], ignorar=pid) == []


def test_proximo_slot_pula_cedo_demais_e_ocupados():
    _pedido("aguardando_envio", "2026-09-29T10:00:00-03:00")
    agora = datetime(2026, 9, 28, 15, 0, tzinfo=SP)
    canal = [datetime(2026, 9, 28, 20, 0, tzinfo=SP)]
    r = slots.proximo_slot(agora, ["10:00", "16:00", "20:00"], canal, antecedencia_min=90)
    assert r == datetime(2026, 9, 29, 16, 0, tzinfo=SP)
    assert r.utcoffset() == timedelta(hours=-3)


def test_proximo_slot_no_mesmo_dia_quando_cabe():
    agora = datetime(2026, 9, 28, 14, 0, tzinfo=SP)
    assert slots.proximo_slot(agora, ["16:00"], [], antecedencia_min=90) == datetime(2026, 9, 28, 16, 0, tzinfo=SP)


def test_sem_slot_em_60_dias_levanta_erro():
    agora = datetime(2026, 9, 28, 8, 0, tzinfo=SP)
    canal = [datetime(2026, 9, 28, 10, 0, tzinfo=SP) + timedelta(days=d) for d in range(61)]
    with pytest.raises(slots.Erro) as e:
        slots.proximo_slot(agora, ["10:00"], canal)
    assert "nenhum slot livre nos proximos 60 dias" in str(e.value)
