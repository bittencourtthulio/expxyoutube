"""Regras dos hooks por agente: escopo de escrita, Bash por lista de permissão e somente leitura.

Chamado pelos wrappers escopo.sh, bash-permitido.sh e somente-leitura.sh com o evento do Claude Code
no stdin. Sai com 2 (bloqueia, com o motivo no stderr) ou 0. O caminho é normalizado com realpath
contra CLAUDE_PROJECT_DIR: `cerebro/../editorial/voz.md` não passa por começar com `cerebro/`.
"""
import json
import os
import re
import sys
from fnmatch import fnmatch
from pathlib import Path

# Onde cada agente pode gravar (padrões relativos à raiz do repositório).
ESCOPO = {
    "curador": ["cerebro/videos/*", "cerebro/INDEX.md", "cerebro/README.md"],
    "bibliotecario": ["biblioteca/videos/*", "biblioteca/INDEX.md", "biblioteca/README.md"],
    "analista": ["editorial/*.md", "editorial/analises/relatorios/*"],
    "roteirista": ["roteiros/*"],
    "planejador": ["planejamento/*", "editorial/*.md"],
    # só o deck.json: estado.json (score, status) e fila.json passam pelo script, nunca pela mão do agente (D-27, D-44)
    "apresentador": ["apresentacoes/decks/*/deck.json"],
}

PY = r"(?:python3|\.venv/bin/python)"
LEITURA_DAS_BASES = rf"{PY} (?:cerebro|biblioteca)\.py (?:buscar|status|canais)(?: .*)?"
DAILY_DA_ROTINA = rf"{PY} daily\.py (?:pendentes|regras|lista|ver|kpis|dia|dias|revisar|saude|responder)(?: .*)?"
# Um comando simples por chamada; nada de encadear, redirecionar ou substituir.
BASH = {
    "curador": [rf"{PY} cerebro\.py (?:pendentes|validar|indice|buscar|status|canais)(?: .*)?"],
    "bibliotecario": [rf"{PY} biblioteca\.py (?:pendentes|validar|indice|buscar|status|canais)(?: .*)?"],
    "analista": [rf"{PY} editorial/analises/(?:coletar_youtube|diagnostico|consultar_cerebro)\.py(?: .*)?",
                 DAILY_DA_ROTINA, LEITURA_DAS_BASES, rf"{PY} decisoes\.py (?:registrar|lista)(?: .*)?"],
    "roteirista": [rf"{PY} \.claude/skills/thumbs-youtube/scripts/validar\.py (?:validar|fingerprints)(?: .*)?", LEITURA_DAS_BASES, rf"{PY} daily\.py (?:regras|ver|responder)(?: .*)?"],
    "planejador": [rf"{PY} planejar\.py(?: .*)?", DAILY_DA_ROTINA, LEITURA_DAS_BASES, rf"{PY} decisoes\.py(?: .*)?",
                   rf"{PY} editorial/analises/(?:diagnostico|consultar_cerebro)\.py(?: .*)?"],
    # apresentador escreve o deck e renderiza; validador pontua e alimenta a fila. Nenhum dos dois roda node ou npx (D-27, D-51).
    "apresentador": [rf"{PY} apresentacao\.py (?:slug|marca|ler|screenshot|validar-deck|render|abrir|referencia|candidatas|lista)(?: .*)?",
                     LEITURA_DAS_BASES, rf"{PY} editorial/analises/consultar_cerebro\.py(?: .*)?"],
    "validador": [rf"{PY} apresentacao\.py (?:validar|pauta|referencia|candidatas|lista)(?: .*)?", LEITURA_DAS_BASES],
}
METACARACTERES = re.compile(r"[;&|<>`$(){}\\\n]")
SO_O_USUARIO = re.compile(r"--autor[ =]usuario\b|daily\.py (?:novo|revogar|cancelar|finalizar)\b")
MUTACAO = re.compile(r"(^|[\s;&|])(rm|mv|cp|mkdir|chmod|chown|touch|tee|dd|truncate|pip|uv|npm|git (?:commit|push|add|reset|checkout|rebase|merge|stash))\b"
                     r"|>|sed\s+-i|perl\s+-i|--refazer|publicacao\.py\s+enviar\b|shorts\.py\s+(?:agendar|reconciliar|liberar|excluir)\b")


def falha(motivo):
    print(f"[hook] {motivo}", file=sys.stderr)
    sys.exit(2)


def relativo(caminho, raiz):
    alvo = Path(caminho)
    alvo = Path(os.path.realpath(alvo if alvo.is_absolute() else raiz / alvo))
    try:
        return alvo.relative_to(Path(os.path.realpath(raiz))).as_posix()
    except ValueError:
        return None


def escopo(agente, evento, raiz):
    if evento.get("tool_name") not in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        return
    caminho = (evento.get("tool_input") or {}).get("file_path") or (evento.get("tool_input") or {}).get("notebook_path")
    rel = relativo(caminho or "", raiz) if caminho else None
    if rel is None or not any(fnmatch(rel, p) for p in ESCOPO.get(agente, [])):
        falha(f"{agente} não grava em {caminho!r}. Escopo: {', '.join(ESCOPO.get(agente, [])) or 'nenhum'}. "
              "Peça ao agente dono do arquivo pela daily ou pelo planejador.")


def bash_permitido(agente, evento):
    if evento.get("tool_name") != "Bash":
        return
    comando = ((evento.get("tool_input") or {}).get("command") or "").strip()
    if METACARACTERES.search(comando):
        falha("um comando simples por vez: sem ; & | < > $ ( ) { } ` \\ nem quebra de linha.")
    if SO_O_USUARIO.search(comando):
        falha("criar, revogar, cancelar ou finalizar fio da daily, e falar como usuario, é só do Usuário.")
    if not any(re.fullmatch(p, comando) for p in BASH.get(agente, [])):
        falha(f"comando fora da lista do {agente}: {comando[:120]!r}")


def somente_leitura(evento):
    nome = evento.get("tool_name")
    if nome in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        falha("agente de revisão só lê: aponte o problema, não corrija.")
    if nome == "Bash" and MUTACAO.search((evento.get("tool_input") or {}).get("command") or ""):
        falha("agente de revisão só lê: esse comando altera arquivo ou repositório.")


def main():
    modo = sys.argv[1]
    agente = sys.argv[2] if len(sys.argv) > 2 else ""
    try:
        evento = json.load(sys.stdin)
    except ValueError:
        falha("evento do hook ilegível")
    raiz = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    if modo == "escopo":
        escopo(agente, evento, raiz)
    elif modo == "bash":
        bash_permitido(agente, evento)
    elif modo == "leitura":
        somente_leitura(evento)
    sys.exit(0)


if __name__ == "__main__":
    main()
