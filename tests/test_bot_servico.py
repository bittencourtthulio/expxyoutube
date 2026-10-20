"""bot_youtube.servico: LaunchAgent próprio (com.canal.telegram-bot-youtube) e uma instância só."""
import fcntl
import plistlib

import pytest

from bot_youtube import pedidos, servico


@pytest.fixture(autouse=True)
def estado(tmp_path, monkeypatch):
    monkeypatch.setattr(pedidos, "ESTADO", tmp_path / "estado")


def test_instalar_grava_plist_proprio_e_carrega(tmp_path):
    chamadas = []
    arq = servico.instalar(pasta=tmp_path / "LaunchAgents", launchctl=lambda cmd: chamadas.append(cmd) or 0)
    plist = plistlib.loads(arq.read_bytes())
    assert arq.name == "com.canal.telegram-bot-youtube.plist" and plist["Label"] == "com.canal.telegram-bot-youtube"
    assert plist["ProgramArguments"][-2:] == [str(servico.RAIZ / "bot_youtube.py"), "rodar"]
    assert plist["EnvironmentVariables"]["TZ"] == "America/Sao_Paulo" and plist["KeepAlive"] is True
    assert servico.ROTULO != "com.canal.telegram-bot"
    assert any("bootstrap" in c for c in chamadas)
    assert not any(k.startswith("TELEGRAM") for k in plist["EnvironmentVariables"])


def test_segunda_instancia_sai_1(tmp_path, capsys):
    trava = servico.trava_de_instancia()
    assert trava is not None
    assert servico.rodar() == 1
    assert "já está rodando" in capsys.readouterr().out
    trava.close()


def test_desinstalar_remove_o_plist(tmp_path):
    pasta = tmp_path / "LaunchAgents"
    servico.instalar(pasta=pasta, launchctl=lambda cmd: 0)
    servico.desinstalar(pasta=pasta, launchctl=lambda cmd: 0)
    assert not (pasta / "com.canal.telegram-bot-youtube.plist").exists()
