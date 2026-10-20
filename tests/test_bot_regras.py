"""T-04.07: as regras do squad e do cursos-ia reconhecem o bot do YouTube como autorização de publicar (D-03, D-04)."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FRASE = "link enviado ao bot do YouTube + Aprovar ou prazo = autorização de publicar no principal"
ARQUIVOS = [RAIZ / ".claude/rules/bot-youtube.md", RAIZ / "CLAUDE.md", RAIZ / ".claude/rules/publicacao.md",
            RAIZ / ".claude/skills/publicar-youtube/SKILL.md", RAIZ / "docs/integracao-produtor.md"]


def test_frase_regra_nos_cinco_arquivos():
    faltam = [str(a.relative_to(RAIZ.parent)) for a in ARQUIVOS if FRASE not in a.read_text(encoding="utf-8")]
    assert faltam == []


def test_regra_do_bot_cita_slots_prazo_canal_e_cancelamento():
    texto = ARQUIVOS[0].read_text(encoding="utf-8")
    for termo in ("YT_SLOTS", "1 h antes do slot", "principal", "UC_EXEMPLO_CONFIGURE_O_SEU", "fica privado", "com.canal.telegram-bot-youtube"):
        assert termo in texto, termo
