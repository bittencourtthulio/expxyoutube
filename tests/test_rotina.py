"""rotina.sh: rotina conhecida, trava, log e claude -p em dontAsk (nunca bypassPermissions)."""
import os
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def projeto(tmp_path):
    shutil.copy(RAIZ / "rotina.sh", tmp_path / "rotina.sh")
    falso = tmp_path / "claude-falso"
    falso.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$(dirname "$0")/argumentos.txt"\necho "resultado ok"\n')
    falso.chmod(0o755)
    return tmp_path


def roda(projeto, *args):
    env = {**os.environ, "CLAUDE_BIN": str(projeto / "claude-falso")}
    return subprocess.run(["bash", str(projeto / "rotina.sh"), *args], cwd=projeto, env=env, capture_output=True, text=True, timeout=30)


def test_rotina_desconhecida_sai_64(projeto):
    r = roda(projeto, "apagar-tudo")
    assert r.returncode == 64 and "rotina desconhecida" in r.stderr
    assert not (projeto / "argumentos.txt").exists()


def test_manha_chama_o_claude_em_dontask_e_grava_log(projeto):
    r = roda(projeto, "manha")
    assert r.returncode == 0, r.stderr
    argumentos = (projeto / "argumentos.txt").read_text().splitlines()
    assert argumentos[0] == "-p" and argumentos[1] == "/rotina-da-manha"
    assert argumentos[argumentos.index("--permission-mode") + 1] == "dontAsk"
    assert "bypassPermissions" not in argumentos
    negadas = argumentos[argumentos.index("--disallowedTools") + 1]
    assert "tokens/" in negadas and "client_secret" in negadas and ".env" in negadas
    log = projeto / "planejamento" / "logs" / f"{date.today().isoformat()}_manha.log"
    texto = log.read_text()
    assert "início: /rotina-da-manha" in texto and "resultado ok" in texto and "fim: /rotina-da-manha (código 0)" in texto
    assert not (projeto / "planejamento" / ".rotina-manha.lock").exists()


def test_argumentos_passam_para_o_comando(projeto):
    assert roda(projeto, "cerebro-atualizar", "20").returncode == 0
    assert (projeto / "argumentos.txt").read_text().splitlines()[1] == "/cerebro-atualizar 20"


@pytest.mark.parametrize("rotina", ["cerebro-descobrir", "biblioteca-descobrir"])
def test_descoberta_e_rotina_conhecida(projeto, rotina):
    assert roda(projeto, rotina).returncode == 0
    assert (projeto / "argumentos.txt").read_text().splitlines()[1] == f"/{rotina}"


def test_trava_viva_sai_zero_sem_chamar_o_claude(projeto):
    (projeto / "planejamento").mkdir()
    (projeto / "planejamento" / ".rotina-manha.lock").mkdir()
    r = roda(projeto, "manha")
    assert r.returncode == 0
    assert not (projeto / "argumentos.txt").exists()
    log = next((projeto / "planejamento" / "logs").glob("*_manha.log")).read_text()
    assert "já está rodando" in log


def test_sintaxe_do_script():
    assert subprocess.run(["bash", "-n", str(RAIZ / "rotina.sh")]).returncode == 0


def test_shorts_roda_o_script_direto_sem_chamar_o_claude(projeto):
    (projeto / "shorts.py").write_text("import sys\nprint('shorts rodou', *sys.argv[1:])\n")
    r = roda(projeto, "shorts", "--simular")
    assert r.returncode == 0, r.stderr
    assert not (projeto / "argumentos.txt").exists()
    log = projeto / "planejamento" / "logs" / f"{date.today().isoformat()}_shorts.log"
    assert "shorts rodou agendar --simular" in log.read_text()
