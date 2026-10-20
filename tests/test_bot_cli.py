"""bot_youtube.py (CLI): verificar confere bot, chat, slots e canal sem imprimir o token."""
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from tests.falsos_bot import FIX

RAIZ = Path(__file__).resolve().parents[1]
TOKEN = "777:segredo-do-bot-youtube"


@pytest.fixture
def servidor_telegram():
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            corpo = json.dumps({"ok": True, "result": {"username": "bot_teste"}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(corpo)

        def log_message(self, *a):
            pass
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def _env(tmp_path, base, canal_json):
    alvo = tmp_path / "canal.json"
    alvo.write_text(Path(canal_json).read_text())
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ}
    env.update({"TELEGRAM_YT_BOT_TOKEN": TOKEN, "TELEGRAM_YT_CHATID": "123456789", "YT_SLOTS": "10:00,16:00",
                "TELEGRAM_API_BASE": base, "BOT_YT_CANAL_FALSO": str(alvo)})
    return env


def _verificar(env):
    return subprocess.run([sys.executable, str(RAIZ / "bot_youtube.py"), "verificar"], cwd=RAIZ, env=env,
                          capture_output=True, text=True, timeout=60)


def test_verificar_em_subprocesso_contra_falsos_sai_0(servidor_telegram, tmp_path):
    p = _verificar(_env(tmp_path, servidor_telegram, FIX / "canal-falso.json"))
    assert p.returncode == 0, p.stderr
    assert "@bot_teste" in p.stdout and "UC_EXEMPLO_CONFIGURE_O_SEU" in p.stdout and "10:00, 16:00" in p.stdout
    assert TOKEN not in p.stdout + p.stderr


def test_verificar_canal_errado_sai_1_citando_o_esperado(servidor_telegram, tmp_path):
    outro = tmp_path / "outro.json"
    outro.write_text(json.dumps({**json.loads((FIX / "canal-falso.json").read_text()), "canal_id": "UCoutro"}))
    p = _verificar(_env(tmp_path, servidor_telegram, outro))
    assert p.returncode == 1 and "UC_EXEMPLO_CONFIGURE_O_SEU" in p.stdout + p.stderr
    assert TOKEN not in p.stdout + p.stderr


# --- T-04.05 CLI completa --------------------------------------------------------------------------

def _cli(tmp_path, *args, extra=None):
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ}
    env.update({"BOT_YT_ESTADO": str(tmp_path / "estado"), **(extra or {})})
    return subprocess.run([sys.executable, str(RAIZ / "bot_youtube.py"), *args], cwd=RAIZ, env=env, capture_output=True, text=True, timeout=60)


def test_novo_cria_pedido_na_fila_e_fila_json_lista(tmp_path):
    p = _cli(tmp_path, "novo", "--url", "https://youtu.be/x", "--modo", "motion")
    assert p.returncode == 0, p.stderr
    pid = p.stdout.strip().split()[-1]
    fila = json.loads(_cli(tmp_path, "fila", "--json").stdout)
    assert [(x["pedido"], x["etapa"], x["modo"]) for x in fila] == [(pid, "na_fila", "motion")]
    assert not (RAIZ / "estado/bot-youtube" / "pedidos" / pid).exists()


def test_aprovar_inexistente_sai_1_e_desagendar_tira_publishat(tmp_path):
    p = _cli(tmp_path, "aprovar", "nao-existe")
    assert p.returncode == 1 and "não existe" in p.stdout + p.stderr
    canal = tmp_path / "canal.json"
    canal.write_text(json.dumps({"canal_id": "UC_EXEMPLO_CONFIGURE_O_SEU", "videos": {
        "v9": {"privacyStatus": "private", "publishAt": "2026-09-29T19:00:00Z", "embeddable": True}}}))
    p = _cli(tmp_path, "desagendar", "v9", extra={"BOT_YT_CANAL_FALSO": str(canal)})
    assert p.returncode == 0, p.stderr
    status = json.loads(canal.read_text())["videos"]["v9"]
    assert status["privacyStatus"] == "private" and "publishAt" not in status and status["embeddable"] is True
