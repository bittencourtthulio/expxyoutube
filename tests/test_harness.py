"""Harness de agentes: frontmatter válido, hooks que existem, equipe na ordem do chat e referências que não apodrecem."""
import json
import re
from pathlib import Path

import chat

RAIZ = Path(__file__).resolve().parents[1]
AGENTES = RAIZ / ".claude" / "agents"


def frontmatter(arq):
    texto = arq.read_text(encoding="utf-8")
    assert texto.startswith("---\n"), f"{arq.name}: sem frontmatter"
    cabeca = texto[4:texto.index("\n---", 4)]
    return cabeca, texto[texto.index("\n---", 4) + 4:]


def campo(cabeca, nome):
    """Valor de uma chave do frontmatter; entende o bloco dobrado `>` do YAML."""
    m = re.search(rf"^{nome}:[ \t]*(.*)$", cabeca, flags=re.M)
    if not m:
        return None
    if m.group(1).strip() in (">", "|", ">-", "|-"):
        linhas = []
        for linha in cabeca[m.end():].splitlines()[1:]:
            if linha and not linha.startswith((" ", "\t")):
                break
            linhas.append(linha.strip())
        return " ".join(l for l in linhas if l)
    return m.group(1).strip()


def test_agentes_da_equipe_com_frontmatter_completo():
    for agente in chat.EQUIPE:
        arq = AGENTES / f"{agente}.md"
        assert arq.exists(), agente
        cabeca, corpo = frontmatter(arq)
        assert campo(cabeca, "name") == agente
        assert campo(cabeca, "description") and len(campo(cabeca, "description")) > 40
        assert campo(cabeca, "tools")
        assert len(corpo.strip()) > 400, f"{agente}: corpo curto demais"


def test_hooks_citados_existem_e_sao_executaveis():
    for arq in AGENTES.glob("*.md"):
        cabeca, _ = frontmatter(arq)
        for script in re.findall(r"\.claude/hooks/([\w.-]+\.sh)", cabeca):
            alvo = RAIZ / ".claude" / "hooks" / script
            assert alvo.exists() and alvo.stat().st_mode & 0o111, f"{arq.name}: {script}"


def test_agentes_com_escrita_ou_bash_tem_hook():
    for arq in AGENTES.glob("*.md"):
        cabeca, _ = frontmatter(arq)
        ferramentas = campo(cabeca, "tools") or ""
        if "Edit" in ferramentas or "Write" in ferramentas:
            assert "escopo.sh" in cabeca, arq.name
        if "Bash" in ferramentas:
            assert "bash-permitido.sh" in cabeca or "somente-leitura.sh" in cabeca, arq.name


def test_equipe_no_disco_bate_com_o_chat_na_mesma_ordem():
    no_disco = sorted(p.stem for p in AGENTES.glob("*.md"))
    assert no_disco == sorted(chat.EQUIPE)
    assert list(chat.EQUIPE) == ["planejador", "analista", "roteirista", "curador", "bibliotecario", "reviewer", "apresentador", "validador"]


def test_agentes_das_apresentacoes_citam_o_metodo():
    validador = (AGENTES / "validador.md").read_text(encoding="utf-8").lower()
    for trecho in ("afinidade", "gancho", "tração", "atualidade", "80", "apresentacao.py referencia", "apresentacao.py validar", "apresentacao.py pauta"):
        assert trecho in validador, trecho
    apresentador = (AGENTES / "apresentador.md").read_text(encoding="utf-8").lower()
    for trecho in ("validar-deck", "apresentacao.py render", "600000", "deck.json", "example.com", "cta", "screenshot"):
        assert trecho in apresentador, trecho
    for texto in (validador, apresentador):
        assert "\u2014" not in texto and "bypassPermissions" not in texto


def test_agentes_nao_falam_do_instagram_nem_liberam_tudo():
    for arq in AGENTES.glob("*.md"):
        texto = arq.read_text(encoding="utf-8")
        assert not re.search(r"carross|Fluxo Privado|permission-mode[ =]bypassPermissions", texto, flags=re.I), arq.name


REGRAS = RAIZ / ".claude" / "rules"
CAMINHO = re.compile(r"`([\w./*<>-]+/[\w./*<>-]*|[\w-]+\.(?:py|md|json|jsonl|sh))`")


RUNTIME = ("estado/", "planejamento/logs", "editorial/analises/dados", "editorial/analises/relatorios/")  # criados pelos scripts, fora do git


def caminhos_citados(texto):
    for c in CAMINHO.findall(texto):
        if any(x in c for x in ("<", "*", "AAAA")) or c.startswith(("http", "--") + RUNTIME):
            continue
        yield c.rstrip("/")


def test_rules_existem_e_citam_so_caminhos_reais():
    esperadas = {"seguranca", "convencoes-gerais", "daily", "rotina-automatica", "cerebro", "biblioteca", "camada-editorial", "apresentacoes"}
    assert esperadas <= {p.stem for p in REGRAS.glob("*.md")}
    gerados = {"diagnostico.json", "leitura.json", "cerebro.json", "chat.jsonl", "daily.jsonl", "decisoes.jsonl", "cota.json",
               "deck.json", "estado.json", "fila.json",  # os três últimos nascem com o primeiro deck (apresentacao.py)
               # estado do bot do YouTube (bot-youtube.md): nasce na primeira subida do bot
               "eventos.jsonl", "pedidos.jsonl", "telegram.json", "bot.log", "bot.lock", "sonda-heygen.json", "publicacao-estado.json"}
    nomes = {p.name for p in RAIZ.rglob("*") if ".venv" not in p.parts and ".git" not in p.parts and "node_modules" not in p.parts}
    for arq in REGRAS.glob("*.md"):
        for c in caminhos_citados(arq.read_text(encoding="utf-8")):
            if "/" not in c:
                assert c in nomes or c in gerados, f"{arq.name} cita {c}, que não existe"
            else:
                assert (RAIZ / c).exists() or (RAIZ / ".claude" / c).exists(), f"{arq.name} cita {c}, que não existe"


def test_rules_sem_instagram_e_bypass_so_na_seguranca():
    for arq in REGRAS.glob("*.md"):
        texto = arq.read_text(encoding="utf-8")
        assert not re.search(r"carross|Fluxo Privado", texto, flags=re.I), arq.name
        if arq.stem != "seguranca":
            assert "bypassPermissions" not in texto, arq.name
    assert "D-41" in (REGRAS / "biblioteca.md").read_text(encoding="utf-8")


def test_camada_editorial_existe():
    for nome in ("voz.md", "aprendizados.md", "cadencia.md"):
        assert len((RAIZ / "editorial" / nome).read_text(encoding="utf-8")) > 200, nome
    assert (RAIZ / "roteiros" / "README.md").exists()


COMANDOS = RAIZ / ".claude" / "commands"
SKILLS = RAIZ / ".claude" / "skills"
CHAMADA = re.compile(r"(?:python3|\.venv/bin/python)\s+([\w/]+\.py)(?:\s+([a-z][\w-]*))?")
_SUBS = {}


def subcomandos(script):
    """Subcomandos do argparse do script, lidos do --help (None se o script não tem subcomando)."""
    if script not in _SUBS:
        import subprocess
        import sys
        ajuda = subprocess.run([sys.executable, script, "--help"], cwd=RAIZ, capture_output=True, text=True, timeout=20).stdout
        m = re.search(r"\{([\w,-]+)\}", ajuda)
        _SUBS[script] = set(m.group(1).split(",")) if m else None
        if script.endswith("diagnostico.py"):
            _SUBS[script] = {"validar-leitura"}
    return _SUBS[script]


def textos_do_harness():
    for arq in list(COMANDOS.glob("*.md")) + list(SKILLS.glob("*/SKILL.md")):
        yield arq, arq.read_text(encoding="utf-8")


def test_commands_e_skills_com_description():
    esperados = {"rotina-da-manha", "analisar-canal", "cerebro-atualizar", "cerebro-canal", "cerebro-descobrir", "biblioteca-atualizar",
                 "biblioteca-canal", "biblioteca-descobrir", "review"}
    assert esperados <= {p.stem for p in COMANDOS.glob("*.md")}
    assert {"analisar-resultados", "rotina-da-manha", "cerebro-youtube", "biblioteca-conteudo", "roteiro-youtube", "apresentacao",
            "validar-pautas"} <= {p.parent.name for p in SKILLS.glob("*/SKILL.md")}
    for arq, texto in textos_do_harness():
        cabeca, _ = frontmatter(arq)
        assert campo(cabeca, "description"), arq


def test_todo_comando_python_citado_existe():
    for arq, texto in textos_do_harness():
        for script, sub in CHAMADA.findall(texto):
            assert (RAIZ / script).exists(), f"{arq}: {script} não existe"
            subs = subcomandos(script)
            if sub and subs is not None:
                assert sub in subs, f"{arq}: {script} {sub} não existe (tem {sorted(subs)})"


def test_harness_sem_instagram_e_sem_bypass():
    for arq, texto in textos_do_harness():
        assert not re.search(r"carross|Fluxo Privado|bypassPermissions", texto, flags=re.I), arq


def test_documentacao_cita_so_comandos_reais():
    for nome in ("README.md", "CLAUDE.md"):
        texto = (RAIZ / nome).read_text(encoding="utf-8")
        for script, sub in CHAMADA.findall(texto):
            assert (RAIZ / script).exists(), f"{nome}: {script}"
            subs = subcomandos(script)
            if sub and subs is not None:
                assert sub in subs, f"{nome}: {script} {sub}"
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    assert re.search(r"^\d+ \d+ \* \* \* .*rotina\.sh manha", readme, flags=re.M)
    assert "rotina.sh cerebro-atualizar" in readme and "rotina.sh biblioteca-atualizar" in readme
    assert "rotina.sh cerebro-descobrir" in readme and "rotina.sh biblioteca-descobrir" in readme
    assert ".venv/bin/python painel.py" in readme
    for trecho in ("/apresentacao", "/pautas", "apresentacao.py render", "apresentacoes/decks", "licen"):
        assert trecho in readme, trecho
    assert "Apresenta" in readme


def test_comandos_rodam_sem_confirmacao_humana():
    """D-45: todo comando slash roda em cron, então nenhum texto do harness pode esperar um sim do Usuário."""
    pede = re.compile(r"confirm\w* (com|do) o? ?Usuário|Só depois do sim|é (decisão|pedido) do Usuário", flags=re.I)
    for arq, texto in textos_do_harness():
        assert not pede.search(texto), f"{arq}: espera confirmação humana"
    for nome in ("cerebro", "biblioteca"):
        cfg = json.loads((RAIZ / nome / "descoberta.json").read_text(encoding="utf-8"))
        assert cfg["consultas"] and cfg["max_canais_por_rodada"] >= 1, nome
        texto = (COMANDOS / f"{nome}-descobrir.md").read_text(encoding="utf-8")
        assert f"{nome}.py descobrir --json" in texto and f"{nome}.py canal add" in texto, nome
        assert "D-45" in (REGRAS / f"{nome}.md").read_text(encoding="utf-8"), nome
