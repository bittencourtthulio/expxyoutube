"""bot_youtube.telegram: cliente mínimo da Bot API, com a rede trocada por HttpFalso."""
import pytest

from bot_youtube import telegram
from tests.falsos_bot import HttpFalso

TOKEN = "777:segredo-do-bot"


def test_429_dorme_retry_after_uma_vez_e_devolve_o_result():
    dormiu = []
    http = HttpFalso({"ok": False, "error_code": 429, "parameters": {"retry_after": 3}}, {"ok": True, "result": {"username": "b"}})
    tg = telegram.Telegram(TOKEN, http=http, dormir=dormiu.append)
    assert tg.chamar("getMe") == {"username": "b"}
    assert dormiu == [3] and len(http.chamadas) == 2


def test_erro_de_rede_com_token_na_url_sai_limpo():
    def http(url, **kw):
        raise ConnectionError(f"falhou ao abrir {url}")
    tg = telegram.Telegram(TOKEN, http=http)
    with pytest.raises(telegram.ErroTelegram) as e:
        tg.chamar("getMe")
    assert TOKEN not in str(e.value) and "<token>" in str(e.value) and e.value.codigo == "rede"


def test_erro_da_api_vira_erro_telegram_com_codigo():
    tg = telegram.Telegram(TOKEN, http=HttpFalso({"ok": False, "error_code": 400, "description": f"bad {TOKEN}"}))
    with pytest.raises(telegram.ErroTelegram) as e:
        tg.chamar("sendMessage", {"chat_id": 1, "text": "x"})
    assert e.value.codigo == 400 and TOKEN not in str(e.value)


def test_url_usa_a_base_configurada():
    http = HttpFalso()
    telegram.Telegram(TOKEN, http=http, api_base="http://127.0.0.1:9").chamar("getMe")
    assert http.chamadas[0]["url"] == f"http://127.0.0.1:9/bot{TOKEN}/getMe"


def test_baixar_arquivo_grava_o_conteudo(tmp_path):
    http = HttpFalso({"ok": True, "result": {"file_path": "voice/f.oga"}})
    urls = []
    tg = telegram.Telegram(TOKEN, http=http, http_get=lambda url, timeout=None: urls.append(url) or b"audio")
    destino = tg.baixar_arquivo("voz1", tmp_path / "a.oga")
    assert destino.read_bytes() == b"audio" and urls[0].endswith("/file/bot" + TOKEN + "/voice/f.oga")
