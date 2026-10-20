"""bot_youtube.executar: processos externos com timeout que mata o grupo."""
import sys
import time

from bot_youtube import executar


def test_timeout_devolve_124_rapido():
    inicio = time.monotonic()
    codigo, saida = executar.rodar([sys.executable, "-c", "import time; time.sleep(5)"], timeout=1)
    assert codigo == 124 and time.monotonic() - inicio < 3 and "1 s" in saida


def test_binario_inexistente_devolve_127_com_o_nome():
    codigo, saida = executar.rodar(["binario-que-nao-existe"])
    assert codigo == 127 and "binario-que-nao-existe" in saida


def test_saida_e_codigo_normais(tmp_path):
    codigo, saida = executar.rodar([sys.executable, "-c", "import os,sys; print(os.getcwd()); sys.exit(2)"], cwd=tmp_path)
    assert codigo == 2 and (str(tmp_path.resolve()) in saida or str(tmp_path) in saida)
