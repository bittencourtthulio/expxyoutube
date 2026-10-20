"""bot_youtube.bot: classificar updates, tratar cliques, ajuste por texto e áudio, avisos (Telegram falso)."""
import json

import pytest

from bot_youtube import bot as botmod
from bot_youtube import fluxo, pedidos, telegram
from tests.falsos_bot import HttpFalso, roteiro_bin, update, updates

CHAT = 123456789


@pytest.fixture(autouse=True)
def estado(tmp_path, monkeypatch):
    monkeypatch.setattr(pedidos, "ESTADO", tmp_path / "estado")
    return tmp_path / "estado"


def _bot(http, **kw):
    tg = telegram.Telegram("1:x", http=http, dormir=lambda s: None, http_get=kw.pop("http_get", lambda url, timeout=None: b"oga"))
    chamadas = {"despachar": 0, "acordar": 0}
    b = botmod.Bot(tg, CHAT, despachar=lambda: chamadas.__setitem__("despachar", chamadas["despachar"] + 1),
                   acordar_envio=lambda: chamadas.__setitem__("acordar", chamadas["acordar"] + 1), **kw)
    return b, chamadas


def _callback(acao, pid, message_id=13):
    return {"update_id": 5000, "callback_query": {"id": "cb", "from": {"id": CHAT}, "data": f"{acao}:{pid}",
                                                  "message": {"message_id": message_id, "chat": {"id": CHAT}}}}


def _pronto(pid=None):
    pid = pid or pedidos.novo_pedido(url="u", etapa="aguardando_escolha")
    fluxo.escolher_modo(pid, "motion")
    pedidos.registrar_evento(pid, "aguardando_envio", avisar=True, horario="2026-09-29T16:00:00-03:00",
                             envio_em="2026-09-29T15:00:00-03:00")
    return pid


# --- T-02.06 classificar ---------------------------------------------------------------------------

def test_cada_update_da_fixture_vira_o_tipo_esperado():
    esperado = {"link_youtube": "link_youtube", "link_outro": "texto", "callback": "callback", "audio": "audio",
                "texto": "texto", "outro_chat": "ignorado"}
    for u in updates():
        assert botmod.classificar(u, CHAT)["tipo"] == esperado[u["_tipo"]], u["_tipo"]


def test_formas_de_link_do_youtube():
    for url in ("https://youtu.be/gWKYOORNW9Q", "https://www.youtube.com/watch?v=gWKYOORNW9Q", "https://youtube.com/shorts/abc",
                "https://m.youtube.com/watch?v=x"):
        u = {"message": {"message_id": 1, "from": {"id": CHAT}, "chat": {"id": CHAT}, "text": f"veja {url}"}}
        c = botmod.classificar(u, CHAT)
        assert c["tipo"] == "link_youtube" and c["url"] == url


# --- T-02.08 tratar cliques ------------------------------------------------------------------------

def test_link_e_escolha_motion_poe_na_fila_e_despacha():
    http = HttpFalso()
    b, ch = _bot(http)
    b.tratar(update("link_youtube"))
    pid = pedidos.pedidos()[-1]["pedido"]
    assert pedidos.estado_pedido(pid)["etapa"] == "aguardando_escolha"
    msg = http.chamadas[-1]["dados"]
    assert "Com avatar" in msg["reply_markup"] and pid in msg["text"]
    b.tratar(_callback("motion", pid))
    assert pedidos.estado_pedido(pid)["etapa"] == "na_fila" and pedidos.estado_pedido(pid)["modo"] == "motion"
    assert ch["despachar"] == 1 and "answerCallbackQuery" in http.metodos()


def test_aprovar_deixa_so_cancelar_e_acorda_o_envio():
    pid = _pronto()
    http = HttpFalso()
    b, ch = _bot(http)
    b.tratar(_callback("aprovar", pid))
    assert pedidos.estado_pedido(pid)["etapa"] == "aprovado" and ch["acordar"] == 1
    edit = next(c for c in http.chamadas if c["metodo"] == "editMessageReplyMarkup")
    assert [bt["text"] for linha in json.loads(edit["dados"]["reply_markup"])["inline_keyboard"] for bt in linha] == ["Cancelar"]


def test_refazer_de_pedido_que_nao_falhou_nao_despacha():
    pid = _pronto()
    http = HttpFalso()
    b, ch = _bot(http)
    b.tratar(_callback("refazer", pid))
    assert ch["despachar"] == 0 and pedidos.estado_pedido(pid)["etapa"] == "aguardando_envio"


def test_cancelar_pelo_botao():
    pid = _pronto()
    b, _ = _bot(HttpFalso())
    b.tratar(_callback("cancelar", pid))
    assert pedidos.estado_pedido(pid)["etapa"] == "cancelado"


# --- T-02.09 ajuste --------------------------------------------------------------------------------

def test_audio_transcrito_vira_ajuste(tmp_path):
    pid = _pronto()
    fluxo.pedir_ajuste(pid)
    env = roteiro_bin(tmp_path, "whisper", arquivos={"{arg:--output_dir}/01.txt": "trocar o gancho\n"})
    http = HttpFalso({"ok": True, "result": True}, {"ok": True, "result": {"file_path": "voice/f.oga"}}, padrao={"ok": True, "result": True})
    b, ch = _bot(http, transcrever_env=env)
    b.tratar(update("audio"))
    e = pedidos.estado_pedido(pid)
    assert e["etapa"] == "ajuste" and e["ajuste"] == "trocar o gancho" and e["ajuste_origem"] == "audio"
    assert (pedidos.pasta_pedido(pid) / "ajustes" / "01.oga").exists() and ch["despachar"] == 1


def test_texto_com_ajuste_pendente_vira_ajuste():
    pid = _pronto()
    fluxo.pedir_ajuste(pid)
    b, _ = _bot(HttpFalso())
    b.tratar(update("texto"))
    assert pedidos.estado_pedido(pid)["ajuste"] == "trocar o gancho"


def test_audio_sem_pedido_esperando_ajuste_so_orienta():
    http = HttpFalso()
    b, _ = _bot(http)
    n = len(pedidos.eventos())
    b.tratar(update("audio"))
    assert len(pedidos.eventos()) == n and "Ajustar" in http.chamadas[-1]["dados"]["text"]


# --- T-02.10 avisos --------------------------------------------------------------------------------

def _previa_pronta(tmp_path):
    pid = pedidos.novo_pedido(url="u", etapa="aguardando_escolha")
    b0 = botmod.Bot(telegram.Telegram("1:x", http=HttpFalso()), CHAT)   # primeira subida: passado não vira mensagem
    b0._salvar()
    fluxo.escolher_modo(pid, "motion")
    (tmp_path / "previa.mp4").write_bytes(b"mp4")
    (tmp_path / "thumb.png").write_bytes(b"png")
    pedidos.registrar_evento(pid, "aguardando_envio", avisar=True, horario="2026-09-29T16:00:00-03:00",
                             envio_em="2026-09-29T15:00:00-03:00", previa=str(tmp_path / "previa.mp4"),
                             thumb=str(tmp_path / "thumb.png"), titulo="Aula X")
    return pid


def test_previa_vai_uma_vez_e_registra_message_id(tmp_path):
    pid = _previa_pronta(tmp_path)
    http = HttpFalso(padrao={"ok": True, "result": {"message_id": 77}})
    b, _ = _bot(http)
    b.avisar()
    b.avisar()
    assert http.metodos().count("sendVideo") == 1 and http.metodos().count("sendPhoto") == 1
    e = pedidos.estado_pedido(pid)
    assert e["message_id"] == 77 and e["etapa"] == "aguardando_envio"
    texto = [c for c in http.chamadas if c["metodo"] == "sendMessage"][-1]["dados"]
    assert "Aprovar" in texto["reply_markup"] and "29/09 às 16:00" in texto["text"]


def test_primeira_subida_nao_manda_o_passado():
    for i in range(5):
        pid = pedidos.novo_pedido(url=f"u{i}", etapa="aguardando_escolha")
        pedidos.registrar_evento(pid, "falhou", avisar=True, nota="velho")
    http = HttpFalso()
    b, _ = _bot(http)
    b.avisar()
    assert http.chamadas == []


def test_falha_manda_botao_refazer():
    http = HttpFalso()
    b, _ = _bot(http)
    b._salvar()
    pid = pedidos.novo_pedido(url="u", etapa="aguardando_escolha")
    pedidos.registrar_evento(pid, "falhou", avisar=True, nota="cota ElevenLabs")
    b.avisar()
    msg = http.chamadas[-1]["dados"]
    assert "cota ElevenLabs" in msg["text"] and "refazer:" in msg["reply_markup"]
