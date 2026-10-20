"""Binário falso roteirizado: lê FALSO_ROTEIRO (JSON {bin: {stdout, stderr, codigo, arquivos, dormir, stdout_arquivo}}),
grava a chamada em FALSO_LOG e cria os arquivos pedidos. `{arg:-o}` vira o argumento depois de -o; `{arg:-1}` o último."""
import json
import os
import sys
import time
from pathlib import Path


def _arg(argv, chave):
    if chave.lstrip("-").isdigit() and chave.startswith("-") and chave[1:].isdigit():
        return argv[int(chave)]
    return argv[argv.index(chave) + 1]


def _troca(texto, argv):
    while "{arg:" in texto:
        i = texto.index("{arg:")
        j = texto.index("}", i)
        texto = texto[:i] + _arg(argv, texto[i + 5:j]) + texto[j + 1:]
    return texto


def main(nome):
    argv = sys.argv[1:]
    log = os.environ.get("FALSO_LOG")
    if log:
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"bin": nome, "argv": argv, "cwd": os.getcwd(),
                                "env": sorted(k for k in os.environ if k.startswith(("TELEGRAM", "YT_", "BOT_YT")))}) + "\n")
    roteiro = json.loads(Path(os.environ["FALSO_ROTEIRO"]).read_text()).get(nome, {}) if os.environ.get("FALSO_ROTEIRO") else {}
    time.sleep(roteiro.get("dormir", 0))
    for caminho, conteudo in (roteiro.get("arquivos") or {}).items():
        destino = Path(_troca(caminho, argv))
        destino.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(conteudo, dict) and "copiar" in conteudo:
            destino.write_bytes(Path(conteudo["copiar"]).read_bytes())
        else:
            destino.write_text(_troca(conteudo, argv), encoding="utf-8")
    if roteiro.get("stdout_arquivo"):
        sys.stdout.write(Path(roteiro["stdout_arquivo"]).read_text(encoding="utf-8"))
    sys.stdout.write(roteiro.get("stdout", ""))
    sys.stderr.write(roteiro.get("stderr", ""))
    sys.exit(roteiro.get("codigo", 0))
