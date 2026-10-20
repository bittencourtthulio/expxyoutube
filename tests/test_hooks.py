"""Hooks do harness: segredos fora do alcance de qualquer sessão; escopo e Bash travados por agente."""
import json
import os
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
HOOKS = RAIZ / ".claude" / "hooks"


def roda(script, entrada, *args, raiz=RAIZ):
    r = subprocess.run([str(HOOKS / script), *args], input=json.dumps(entrada), text=True, capture_output=True,
                       env={**os.environ, "CLAUDE_PROJECT_DIR": str(raiz)})
    return r.returncode, r.stderr


@pytest.mark.parametrize("entrada, bloqueia", [
    ({"tool_name": "Read", "tool_input": {"file_path": str(RAIZ / "tokens" / "principal.json")}}, True),
    ({"tool_name": "Read", "tool_input": {"file_path": "client_secret.json"}}, True),
    ({"tool_name": "Read", "tool_input": {"file_path": str(RAIZ / ".env")}}, True),
    ({"tool_name": "Edit", "tool_input": {"file_path": "tokens/x.json"}}, True),
    ({"tool_name": "Write", "tool_input": {"file_path": "./painel/../tokens/novo.json"}}, True),
    ({"tool_name": "Grep", "tool_input": {"pattern": "refresh", "path": "tokens"}}, True),
    ({"tool_name": "Bash", "tool_input": {"command": "head client_secret.json"}}, True),
    ({"tool_name": "Bash", "tool_input": {"command": "cat ./tokens/../tokens/x.json"}}, True),
    ({"tool_name": "Bash", "tool_input": {"command": "grep -r token .env"}}, True),
    ({"tool_name": "Read", "tool_input": {"file_path": str(RAIZ / "daily.py")}}, False),
    ({"tool_name": "Read", "tool_input": {"file_path": "editorial/voz.md"}}, False),
    ({"tool_name": "Bash", "tool_input": {"command": "python3 editorial/analises/coletar_youtube.py"}}, False),
    ({"tool_name": "Bash", "tool_input": {"command": "python3 daily.py pendentes --json"}}, False),
    ({"tool_name": "Read", "tool_input": {"file_path": "docs/tokens-do-youtube.md"}}, False),
])
def test_guard_de_segredos(entrada, bloqueia):
    codigo, erro = roda("guard-segredos.sh", entrada)
    assert (codigo == 2) == bloqueia, erro
    if bloqueia:
        assert "segredo" in erro


def test_settings_registra_o_guard_em_pretooluse():
    cfg = json.loads((RAIZ / ".claude" / "settings.json").read_text(encoding="utf-8"))
    comandos = [h["command"] for grupo in cfg["hooks"]["PreToolUse"] for h in grupo["hooks"]]
    assert any("guard-segredos.sh" in c for c in comandos)
    assert "bypassPermissions" not in json.dumps(cfg)


def escrita(caminho):
    return {"tool_name": "Write", "tool_input": {"file_path": caminho}}


def bash(comando):
    return {"tool_name": "Bash", "tool_input": {"command": comando}}


@pytest.mark.parametrize("agente, caminho, liberado", [
    ("curador", "cerebro/videos/paddy/nota.md", True),
    ("curador", "cerebro/INDEX.md", True),
    ("curador", "cerebro/../editorial/voz.md", False),
    ("curador", "cerebro/temas.json", False),
    ("curador", "cerebro/canais.json", False),
    ("bibliotecario", "biblioteca/videos/x/nota.md", True),
    ("bibliotecario", "cerebro/videos/x/nota.md", False),
    ("analista", "editorial/aprendizados.md", True),
    ("analista", "editorial/analises/relatorios/2026-09-23/leitura.json", True),
    ("analista", "editorial/analises/diagnostico.py", False),
    ("analista", "painel.py", False),
    ("roteirista", "roteiros/2026-09-23-claude-code.md", True),
    ("roteirista", "editorial/voz.md", False),
    ("planejador", "planejamento/2026-09-23.json", True),
    ("planejador", "editorial/cadencia.md", True),
    ("planejador", "painel.py", False),
    ("apresentador", "apresentacoes/decks/2026-09-23-x/deck.json", True),
    ("apresentador", "apresentacoes/decks/2026-09-23-x/estado.json", False),
    ("apresentador", "apresentacoes/motion/src/Root.tsx", False),
    ("apresentador", "apresentacoes/comuns/marcas.json", False),
    ("validador", "apresentacoes/decks/2026-09-23-x/deck.json", False),
    ("validador", "apresentacoes/fila.json", False),
])
def test_escopo_de_escrita(agente, caminho, liberado, tmp_path):
    codigo, erro = roda("escopo.sh", escrita(caminho), agente, raiz=tmp_path)
    assert (codigo == 0) == liberado, erro


@pytest.mark.parametrize("agente, comando, liberado", [
    ("curador", "python3 cerebro.py validar", True),
    ("curador", ".venv/bin/python cerebro.py pendentes --json", True),
    ("curador", "python3 cerebro.py validar; rm -rf x", False),
    ("curador", "python3 cerebro.py importar canal", False),
    ("curador", "python3 cerebro.py buscar --texto $(whoami)", False),
    ("bibliotecario", "python3 biblioteca.py buscar --tema agentes --ideias", True),
    ("bibliotecario", "python3 cerebro.py validar", False),
    ("analista", "python3 editorial/analises/diagnostico.py validar-leitura", True),
    ("analista", "python3 daily.py responder d001 --autor analista --texto oi", True),
    ("analista", "python3 daily.py novo --tipo tarefa --texto x", False),
    ("analista", "python3 daily.py responder d001 --autor usuario --texto x", False),
    ("analista", "git push", False),
    ("roteirista", "python3 biblioteca.py buscar --tema agentes --ideias", True),
    ("roteirista", "python3 editorial/analises/coletar_youtube.py", False),
    ("planejador", "python3 planejar.py criar --json", True),
    ("planejador", "python3 decisoes.py registrar --tipo pauta --o-que x --por-que y --evidencia z --como-desfazer w", True),
    ("planejador", "python3 daily.py revogar d002", False),
    ("planejador", "curl https://example.com", False),
    ("apresentador", "python3 apresentacao.py slug --titulo 'Supabase no lugar do backend'", True),
    ("apresentador", "python3 apresentacao.py marca https://supabase.com --deck 2026-09-23-x", True),
    ("apresentador", "python3 apresentacao.py ler https://supabase.com/docs", True),
    ("apresentador", "python3 apresentacao.py screenshot --deck 2026-09-23-x", True),
    ("apresentador", "python3 apresentacao.py validar-deck 2026-09-23-x", True),
    ("apresentador", ".venv/bin/python apresentacao.py render 2026-09-23-x", True),
    ("apresentador", "python3 apresentacao.py abrir 2026-09-23-x", True),
    ("apresentador", "python3 apresentacao.py referencia --json", True),
    ("apresentador", "python3 apresentacao.py candidatas --json", True),
    ("apresentador", "python3 editorial/analises/consultar_cerebro.py --para roteiro", True),
    ("apresentador", "python3 biblioteca.py buscar --tema agentes --ideias", True),
    ("apresentador", "python3 apresentacao.py validar 2026-09-23-x --score 90 --motivo x", False),
    ("apresentador", "python3 apresentacao.py status 2026-09-23-x gravada", False),
    ("apresentador", "python3 apresentacao.py pauta --titulo x --angulo y --origem z --score 90 --motivo m", False),
    ("apresentador", "npx remotion render src/index.ts slide-1 out.mp4", False),
    ("apresentador", "python3 apresentacao.py ler https://x.dev/?a=1&b=2", False),
    ("validador", "python3 apresentacao.py validar 2026-09-23-x --score 85 --motivo 'afinidade 22/25 com o top views'", True),
    ("validador", "python3 apresentacao.py pauta --titulo x --angulo y --origem z --score 84 --motivo m", True),
    ("validador", "python3 apresentacao.py referencia --json", True),
    ("validador", "python3 apresentacao.py candidatas --json", True),
    ("validador", "python3 apresentacao.py lista --json", True),
    ("validador", "python3 cerebro.py buscar --tema ideias --praticas", True),
    ("validador", "python3 apresentacao.py render 2026-09-23-x", False),
    ("validador", "python3 apresentacao.py status 2026-09-23-x gravada", False),
    ("validador", "python3 editorial/analises/diagnostico.py", False),
    ("validador", "npx remotion still src/index.ts slide-1 x.png", False),
])
def test_bash_por_lista_de_permissao(agente, comando, liberado):
    codigo, erro = roda("bash-permitido.sh", bash(comando), agente)
    assert (codigo == 0) == liberado, erro


@pytest.mark.parametrize("entrada, liberado", [
    ({"tool_name": "Read", "tool_input": {"file_path": "painel.py"}}, True),
    ({"tool_name": "Edit", "tool_input": {"file_path": "painel.py"}}, False),
    (bash("git diff"), True),
    (bash("python3 publicacao.py enviar plano.json --state estado.json"), False),
    (bash("python3 publicacao.py validar plano.json"), True),
    (bash("python3 publicacao.py verificar plano.json --state estado.json"), True),
    (bash(".venv/bin/python -m pytest -q"), True),
    (bash("rm -rf painel"), False),
    (bash("git commit -m x"), False),
    (bash("echo x > painel.py"), False),
    (bash("sed -i '' s/a/b/ painel.py"), False),
])
def test_somente_leitura(entrada, liberado):
    codigo, erro = roda("somente-leitura.sh", entrada)
    assert (codigo == 0) == liberado, erro
