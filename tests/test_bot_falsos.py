"""Os falsos do bot do YouTube: HttpFalso, updates de exemplo e binários falsos roteirizados."""
import json
import os
import subprocess

from tests.falsos_bot import BIN_FALSO, FIX, HttpFalso, roteiro_bin, updates

CHAT = 123456789


def test_http_falso_devolve_em_ordem_e_registra():
    http = HttpFalso({"ok": False, "error_code": 429, "parameters": {"retry_after": 1}}, {"ok": True, "result": 1})
    a = http("https://x/bot1/getMe", dados={"a": 1})
    b = http("https://x/bot1/getMe")
    assert a[1]["error_code"] == 429 and b[1]["result"] == 1
    assert [c["metodo"] for c in http.chamadas] == ["getMe", "getMe"]
    assert http.chamadas[0]["dados"] == {"a": 1}


def test_updates_tem_um_de_cada_tipo():
    tipos = [u["_tipo"] for u in updates()]
    assert sorted(tipos) == sorted(["link_youtube", "link_outro", "callback", "audio", "texto", "outro_chat"])
    assert all(u["message"]["chat"]["id"] != CHAT for u in updates() if u["_tipo"] == "outro_chat")


def test_binarios_falsos_sao_executaveis():
    for nome in ("claude", "yt-dlp", "whisper"):
        assert os.access(BIN_FALSO / nome, os.X_OK), nome


def test_binario_falso_segue_o_roteiro(tmp_path):
    saida = tmp_path / "saida"
    env = roteiro_bin(tmp_path, "yt-dlp", stdout="baixado", codigo=3, arquivos={"{arg:-o}.txt": "conteudo"})
    p = subprocess.run([str(BIN_FALSO / "yt-dlp"), "-o", str(saida), "url"], capture_output=True, text=True, env=env)
    assert p.returncode == 3 and "baixado" in p.stdout
    assert (tmp_path / "saida.txt").read_text() == "conteudo"
    log = [json.loads(l) for l in (tmp_path / "chamadas.jsonl").read_text().splitlines()]
    assert log[0]["bin"] == "yt-dlp" and log[0]["argv"][-1] == "url"


def test_fixtures_existem():
    assert (FIX / "updates.json").exists()
