"""Lógica do guard-segredos.sh (ver o cabeçalho de lá)."""
import json, os, re, sys
from pathlib import Path

try:
    evento = json.load(sys.stdin)
except ValueError:
    sys.exit(0)
raiz = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
entrada = evento.get("tool_input") or {}


def segredo_no_caminho(caminho):
    if not caminho:
        return False
    alvo = Path(caminho)
    alvo = (alvo if alvo.is_absolute() else raiz / alvo).resolve()
    try:
        rel = alvo.relative_to(raiz)
    except ValueError:
        rel = alvo
    partes = rel.parts
    return (bool(partes) and partes[0] == "tokens") or alvo.name.startswith("client_secret") or alvo.name == ".env"


SEGREDO_NO_TEXTO = re.compile(r"(^|[\s/'\"=:(<])(tokens/|tokens$|tokens[\s;|&)]|client_secret|\.env(?![\w.-]))")

bloqueia = False
for chave in ("file_path", "path", "notebook_path"):
    if segredo_no_caminho(entrada.get(chave)):
        bloqueia = True
comando = entrada.get("command") or ""
if comando and SEGREDO_NO_TEXTO.search(comando):
    bloqueia = True
if bloqueia:
    print("[guard] acesso a segredo bloqueado: tokens/, client_secret*.json e .env ficam fora do alcance da IA. "
          "Os scripts (auth.py, yt.py) abrem o token pelo apelido do canal; use-os.", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
