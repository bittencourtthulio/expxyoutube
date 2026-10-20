"""bot_youtube.sonda_heygen: prova que o claude sem cabeça chama o MCP heygen de verdade (não só escreve um número)."""
import json

import pytest

from bot_youtube import executar, sonda_heygen
from tests.falsos_bot import FIX, chamadas_bin, roteiro_bin


@pytest.fixture
def estado(tmp_path, monkeypatch):
    monkeypatch.setattr(sonda_heygen, "ESTADO", tmp_path / "estado")
    return tmp_path / "estado"


def _rodar(tmp_path, stream, estado):
    env = roteiro_bin(tmp_path, "claude", stdout_arquivo=str(FIX / stream))
    r = sonda_heygen.sondar(cursos_ia=tmp_path, executar=lambda cmd, timeout, cwd: executar.rodar(cmd, timeout=timeout, cwd=cwd, env=env))
    gravado = json.loads((estado / "sonda-heygen.json").read_text())
    assert gravado == r
    return r


def test_tool_use_com_resultado_real_da_ok_true(tmp_path, estado):
    r = _rodar(tmp_path, "stream-heygen-ok.jsonl", estado)
    assert r["ok"] is True and r["creditos"] == 1276 and r["usuario"] == "usuario@exemplo.com"
    chamada = chamadas_bin(tmp_path)[0]
    cmd = chamada["argv"]
    assert "--verbose" in cmd and cmd[cmd.index("--output-format") + 1] == "stream-json"
    assert cmd[cmd.index("--allowedTools") + 1] == "mcp__heygen__get_current_user"
    assert "--mcp-config" not in cmd and chamada["cwd"] in (str(tmp_path), str(tmp_path.resolve()))


def test_numero_sem_chamar_a_ferramenta_da_ok_false(tmp_path, estado):
    r = _rodar(tmp_path, "stream-heygen-sem-tool.jsonl", estado)
    assert r["ok"] is False and r["motivo"] == "ferramenta heygen nao chamada"


def test_ferramenta_negada_da_ok_false(tmp_path, estado):
    r = _rodar(tmp_path, "stream-heygen-negado.jsonl", estado)
    assert r["ok"] is False and "erro" in r["motivo"]


def test_claude_ausente_da_ok_false(tmp_path, estado):
    r = sonda_heygen.sondar(cursos_ia=tmp_path, executar=lambda cmd, timeout, cwd: (127, "claude não está no PATH"))
    assert r["ok"] is False and "127" in r["motivo"]
