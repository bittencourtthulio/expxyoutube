"""Sonda do MCP heygen num claude sem cabeça (D-06, D-27).

Roda `claude -p` com cwd no cursos-ia, onde o servidor heygen do escopo local carrega com o OAuth do Claude Code,
e pede só `get_current_user`. `ok` só é true se o stream mostra o tool_use dessa ferramenta e um tool_result sem
erro com o usuário: número escrito pelo modelo sem chamar a ferramenta não conta.

  python3 -m bot_youtube.sonda_heygen      # grava estado/bot-youtube/sonda-heygen.json
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from comum import SP

from . import executar as _executar

from .pedidos import ESTADO  # noqa: E402 - mesma pasta de estado do bot (BOT_YT_ESTADO)
FERRAMENTA = "mcp__heygen__get_current_user"
PEDIDO = (f"Chame a ferramenta {FERRAMENTA} uma vez e responda só um JSON "
          '{"creditos": <premium_credits.remaining>, "usuario": <email>}. Não chame nenhuma outra ferramenta.')


def comando():
    return ["claude", "-p", PEDIDO, "--output-format", "stream-json", "--verbose", "--allowedTools", FERRAMENTA]


def _texto(conteudo):
    if isinstance(conteudo, str):
        return conteudo
    return "".join(c.get("text", "") for c in conteudo or [] if isinstance(c, dict))


def ler_stream(saida):
    chamou, resultado = None, None
    for linha in saida.splitlines():
        try:
            ev = json.loads(linha)
        except ValueError:
            continue
        for c in (ev.get("message") or {}).get("content") or []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use" and c.get("name") == FERRAMENTA:
                chamou = c.get("id")
            elif c.get("type") == "tool_result" and chamou and c.get("tool_use_id") == chamou:
                resultado = c
    if not chamou:
        return {"ok": False, "motivo": "ferramenta heygen nao chamada"}
    if not resultado:
        return {"ok": False, "motivo": "ferramenta heygen sem resultado"}
    texto = _texto(resultado.get("content"))
    if resultado.get("is_error"):
        return {"ok": False, "motivo": f"ferramenta heygen com erro: {texto[:200]}"}
    try:
        dados = json.loads(texto)
    except ValueError:
        return {"ok": False, "motivo": f"resultado da ferramenta heygen sem JSON: {texto[:200]}"}
    usuario = dados.get("email") or dados.get("username") or (dados.get("data") or {}).get("email")
    creditos = ((dados.get("premium_credits") or (dados.get("data") or {}).get("premium_credits") or {}).get("remaining"))
    if not usuario:
        return {"ok": False, "motivo": "resultado da ferramenta heygen sem usuario"}
    return {"ok": True, "usuario": usuario, "creditos": creditos}


def sondar(cursos_ia, executar=None, timeout=300):
    rodar = executar or (lambda cmd, timeout, cwd: _executar.rodar(cmd, timeout=timeout, cwd=cwd, limite_saida=200_000))
    codigo, saida = rodar(comando(), timeout, str(cursos_ia))
    r = ler_stream(saida) if codigo == 0 else {"ok": False, "motivo": f"claude saiu {codigo}: {saida.strip()[-200:]}"}
    r["quando"] = datetime.now(SP).isoformat(timespec="seconds")
    ESTADO.mkdir(parents=True, exist_ok=True)
    (ESTADO / "sonda-heygen.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    return r


def ultima():
    arq = ESTADO / "sonda-heygen.json"
    try:
        return json.loads(arq.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


if __name__ == "__main__":
    from .config import carregar_config
    r = sondar(carregar_config().cursos_ia)
    print(json.dumps({k: v for k, v in r.items() if k != "usuario"}, ensure_ascii=False))
    sys.exit(0 if r["ok"] else 1)
