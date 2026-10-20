"""bot_youtube.enviador: um giro sobe os vencidos, reagenda slot perdido e para no token expirado."""
from datetime import datetime

import pytest

from bot_youtube import config, enviador, fluxo, pedidos
from comum import SP
from tests.falsos_bot import CanalFalso


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setattr(pedidos, "ESTADO", tmp_path / "estado")
    return config.Config(token="1:x", chat_id=1, slots=["10:00", "16:00"], cursos_ia=tmp_path / "cursos-ia")


def _pronto(horario, envio):
    pid = pedidos.novo_pedido(url="u", etapa="aguardando_escolha")
    fluxo.escolher_modo(pid, "motion")
    pedidos.registrar_evento(pid, "aguardando_envio", avisar=True, horario=horario, envio_em=envio)
    return pid


def test_giro_sobe_o_aprovado(cfg, tmp_path):
    pid = _pronto("2026-09-29T16:00:00-03:00", "2026-09-29T15:00:00-03:00")
    fluxo.aprovar(pid, agora=datetime(2026, 9, 28, 10, 0, tzinfo=SP))
    subidos = []

    def enviar(p, c, motivo=None):
        subidos.append((p, motivo))
        pedidos.registrar_evento(p, "enviado", video_id="v1")
        return "enviado"
    feitos = enviador.girar(cfg, agora=datetime(2026, 9, 28, 10, 1, tzinfo=SP), enviar=enviar, cliente_fn=lambda: CanalFalso().cliente(tmp_path))
    assert feitos == [pid] and pedidos.estado_pedido(pid)["etapa"] == "enviado" and "aprovado" in subidos[0][1]


def test_slot_em_10_min_ganha_novo_slot(cfg, tmp_path):
    pid = _pronto("2026-09-28T10:00:00-03:00", "2026-09-28T09:00:00-03:00")
    feitos = enviador.girar(cfg, agora=datetime(2026, 9, 28, 9, 50, tzinfo=SP), enviar=lambda *a, **k: pytest.fail("não sobe"),
                            cliente_fn=lambda: CanalFalso().cliente(tmp_path))
    e = pedidos.estado_pedido(pid)
    assert feitos == [] and e["etapa"] == "reagendado" and e["horario"] == "2026-09-28T16:00:00-03:00"
    assert e["envio_em"] == "2026-09-28T15:00:00-03:00"


def test_token_expirado_bloqueia_com_um_aviso(cfg, tmp_path):
    import yt
    pid = _pronto("2026-09-28T10:00:00-03:00", "2026-09-28T09:00:00-03:00")
    falso = CanalFalso(erro=yt.ErroAuth("credencial expirada; refaça o login: .venv/bin/python auth.py principal"))
    for _ in range(2):
        enviador.girar(cfg, agora=datetime(2026, 9, 28, 9, 50, tzinfo=SP), enviar=lambda *a, **k: pytest.fail("não sobe"),
                       cliente_fn=lambda: falso.cliente(tmp_path))
    e = pedidos.estado_pedido(pid)
    avisos = [x for x in pedidos.eventos(pid) if x["etapa"] == "bloqueado"]
    assert e["etapa"] == "bloqueado" and len(avisos) == 1 and "auth.py" in avisos[0]["nota"] and avisos[0]["avisar"]
