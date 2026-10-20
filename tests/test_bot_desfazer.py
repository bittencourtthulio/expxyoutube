"""T-04.09: o DESFAZER.md do bot lista o LaunchAgent com o comando de volta (regra do AGENTS.md do cursos-ia)."""
from pathlib import Path

DESFAZER = Path(__file__).resolve().parents[1] / "docs/DESFAZER.md"


def test_desfazer_tem_o_bootout_do_launchagent_e_a_remocao_do_plist():
    texto = DESFAZER.read_text(encoding="utf-8")
    assert "launchctl bootout gui/<uid>/com.canal.telegram-bot-youtube" in texto
    assert "~/Library/LaunchAgents/com.canal.telegram-bot-youtube.plist" in texto
    assert "bot_youtube.py desagendar" in texto
