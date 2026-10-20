"""bot_youtube.canal: publishAt agendados, playlists e desagendar no canal (API falsa)."""
from datetime import datetime

import pytest

from bot_youtube import canal
from comum import SP
from tests.falsos_bot import CanalFalso

STATUS = {"license": "youtube", "embeddable": True, "publicStatsViewable": True, "selfDeclaredMadeForKids": False,
          "containsSyntheticMedia": True}


@pytest.fixture
def falso():
    return CanalFalso(videos={
        "v1": {**STATUS, "privacyStatus": "public"},
        "v2": {**STATUS, "privacyStatus": "private", "publishAt": "2026-09-29T13:00:00Z"},
        "v3": {**STATUS, "privacyStatus": "private", "publishAt": "2026-09-29T19:00:00Z"},
    }, playlists=[{"id": "PL1", "titulo": "Claude Code"}, {"id": "PL2", "titulo": "Agentes de IA"}])


def test_agendados_pagina_e_converte_para_sao_paulo(falso, tmp_path):
    horas = canal.agendados(falso.cliente(tmp_path))
    assert horas == [datetime(2026, 9, 29, 10, 0, tzinfo=SP), datetime(2026, 9, 29, 16, 0, tzinfo=SP)]
    assert all(h.tzinfo is not None and h.utcoffset().total_seconds() == -3 * 3600 for h in horas)
    assert "status" in falso.pedidos[0]["part"]


def test_desagendar_tira_publishat_e_preserva_status(falso, tmp_path):
    falso.videos["v2"]["embeddable"] = False
    canal.desagendar(falso.cliente(tmp_path), "v2")
    corpo = falso.atualizacoes[-1]["body"]
    assert corpo["id"] == "v2" and falso.atualizacoes[-1]["part"] == "status"
    assert corpo["status"]["privacyStatus"] == "private" and "publishAt" not in corpo["status"]
    assert corpo["status"]["embeddable"] is False and corpo["status"]["publicStatsViewable"] is True


def test_playlists(falso, tmp_path):
    assert canal.playlists(falso.cliente(tmp_path)) == [{"id": "PL1", "titulo": "Claude Code"}, {"id": "PL2", "titulo": "Agentes de IA"}]


def test_desagendar_video_inexistente_recusa(falso, tmp_path):
    with pytest.raises(canal.ErroCanal):
        canal.desagendar(falso.cliente(tmp_path), "nao-existe")
