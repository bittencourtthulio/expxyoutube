"""bot_youtube.config: variáveis do bot do YouTube, do ambiente e depois do arquivo de chaves da raiz."""
import pytest

from bot_youtube import config

TOKEN = "777:segredo-do-bot-youtube"


def _arquivo(tmp_path, texto):
    arq = tmp_path / "chaves"
    arq.write_text(texto, encoding="utf-8")
    return arq


def test_arquivo_so_com_as_variaveis_do_instagram_cita_a_variavel_do_youtube(tmp_path):
    arq = _arquivo(tmp_path, "TELEGRAM_BOT_TOKEN=1:instagram\nTELEGRAM_CHATID=42\n")
    with pytest.raises(config.ErroConfig) as e:
        config.carregar_config(ambiente={}, arquivo=arq)
    assert "TELEGRAM_YT_BOT_TOKEN" in str(e.value)
    assert "instagram" not in str(e.value)


def test_padroes_e_slots_ordenados(tmp_path):
    arq = _arquivo(tmp_path, f'TELEGRAM_YT_BOT_TOKEN="{TOKEN}"\nTELEGRAM_YT_CHATID=123456789\n')
    cfg = config.carregar_config(ambiente={"YT_SLOTS": "16:00,10:00"}, arquivo=arq)
    assert cfg.slots == ["10:00", "16:00"]
    assert cfg.tempo_producao_min == 240
    assert cfg.antecedencia_min == 90
    assert cfg.disco_min_gb == 8
    assert cfg.canal_alias == "principal"
    assert cfg.canal_id == "UC_EXEMPLO_CONFIGURE_O_SEU"
    assert cfg.token == TOKEN and cfg.chat_id == 123456789


def test_ambiente_vence_o_arquivo(tmp_path):
    arq = _arquivo(tmp_path, "TELEGRAM_YT_BOT_TOKEN=1:arquivo\nTELEGRAM_YT_CHATID=1\nYT_SLOTS=08:00\n")
    cfg = config.carregar_config(ambiente={"TELEGRAM_YT_BOT_TOKEN": "2:amb", "TELEGRAM_YT_CHATID": "7", "YT_SLOTS": "20:00"}, arquivo=arq)
    assert (cfg.token, cfg.chat_id, cfg.slots) == ("2:amb", 7, ["20:00"])


def test_slot_invalido_recusa(tmp_path):
    arq = _arquivo(tmp_path, f"TELEGRAM_YT_BOT_TOKEN={TOKEN}\nTELEGRAM_YT_CHATID=1\n")
    with pytest.raises(config.ErroConfig) as e:
        config.carregar_config(ambiente={"YT_SLOTS": "10:00,25:00"}, arquivo=arq)
    assert "YT_SLOTS" in str(e.value) and TOKEN not in str(e.value)


def test_sem_slots_recusa(tmp_path):
    arq = _arquivo(tmp_path, f"TELEGRAM_YT_BOT_TOKEN={TOKEN}\nTELEGRAM_YT_CHATID=1\n")
    with pytest.raises(config.ErroConfig) as e:
        config.carregar_config(ambiente={}, arquivo=arq)
    assert "YT_SLOTS" in str(e.value)


def test_chat_nao_numerico_nao_vaza_token(tmp_path):
    arq = _arquivo(tmp_path, f"TELEGRAM_YT_BOT_TOKEN={TOKEN}\nTELEGRAM_YT_CHATID=abc\nYT_SLOTS=10:00\n")
    with pytest.raises(config.ErroConfig) as e:
        config.carregar_config(ambiente={}, arquivo=arq)
    assert "TELEGRAM_YT_CHATID" in str(e.value) and TOKEN not in str(e.value)
