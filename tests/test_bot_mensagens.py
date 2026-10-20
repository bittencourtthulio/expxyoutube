"""bot_youtube.mensagens: textos e teclados do bot."""
import json

from bot_youtube import mensagens

PID = "y20260928-150000-12"
ACOES = {"avatar", "motion", "aprovar", "ajustar", "cancelar", "manter", "refazer"}


def _botoes(teclado):
    return [b for linha in json.loads(teclado)["inline_keyboard"] for b in linha]


def test_callback_data_cabe_em_64_bytes_e_tem_acao_conhecida():
    for fn in (mensagens.teclado_modo, mensagens.teclado_previa, mensagens.teclado_ajuste, mensagens.teclado_refazer,
               mensagens.teclado_cancelar):
        for b in _botoes(fn(PID)):
            acao, _, pid = b["callback_data"].partition(":")
            assert len(b["callback_data"].encode()) <= 64 and acao in ACOES and pid == PID


def test_pergunta_do_modo_tem_os_dois_botoes():
    assert [b["text"] for b in _botoes(mensagens.teclado_modo(PID))] == ["Com avatar", "Só motion"]


def test_previa_tem_aprovar_ajustar_cancelar():
    assert [b["text"] for b in _botoes(mensagens.teclado_previa(PID))] == ["Aprovar", "Ajustar", "Cancelar"]


def test_texto_da_previa_diz_horario_e_prazo():
    t = mensagens.texto_previa({"pedido": PID, "horario": "2026-09-29T16:00:00-03:00", "envio_em": "2026-09-29T15:00:00-03:00",
                                "titulo": "Claude Code em 5 minutos"})
    assert "29/09 às 16:00" in t and "sobe sozinho às 15:00" in t and "Claude Code em 5 minutos" in t


def test_avisos_por_etapa():
    assert "falhou" in mensagens.texto_do_aviso({"pedido": PID, "etapa": "falhou", "nota": "cota ElevenLabs"}, {})
    assert "cota ElevenLabs" in mensagens.texto_do_aviso({"pedido": PID, "etapa": "falhou", "nota": "cota ElevenLabs"}, {})
    t = mensagens.texto_do_aviso({"pedido": PID, "etapa": "enviado", "video_id": "abc"}, {"horario": "2026-09-29T16:00:00-03:00"})
    assert "29/09 às 16:00" in t and "abc" in t
    assert "voz concluída" in mensagens.texto_do_aviso({"pedido": PID, "etapa": "progresso", "nota": "voz concluída"}, {})


# --- barra de progresso nos avisos (pedido do Usuário, 28/09/2026) ----------------------------------

def test_barra_de_progresso():
    assert mensagens.barra(0) == "░░░░░░░░░░ 0%"
    assert mensagens.barra(45) == "▓▓▓▓▓░░░░░ 45%"
    assert mensagens.barra(100) == "▓▓▓▓▓▓▓▓▓▓ 100%"
    assert mensagens.barra(130) == "▓▓▓▓▓▓▓▓▓▓ 100%"


def test_aviso_de_progresso_comeca_com_a_barra():
    t = mensagens.texto_do_aviso({"pedido": PID, "etapa": "progresso", "nota": "voz concluída", "pct": 45}, {})
    assert t.splitlines()[0] == "▓▓▓▓▓░░░░░ 45%" and "voz concluída" in t
    t = mensagens.texto_do_aviso({"pedido": PID, "etapa": "produzindo"}, {})
    assert t.splitlines()[0] == "░░░░░░░░░░ 0%"
    sem = mensagens.texto_do_aviso({"pedido": PID, "etapa": "progresso", "nota": "algo"}, {})
    assert "%" not in sem.splitlines()[0]


def test_previa_mostra_100():
    t = mensagens.texto_previa({"pedido": PID, "horario": "2026-09-29T16:00:00-03:00", "envio_em": "2026-09-29T15:00:00-03:00"})
    assert t.splitlines()[0] == "▓▓▓▓▓▓▓▓▓▓ 100%"


def test_percentual_das_etapas_sobe_na_ordem():
    motion = ["preflight", "roteiro", "voz", "legendas", "visual", "render", "pacote"]
    avatar = ["preflight", "roteiro", "saldo", "voz", "avatar", "legendas", "visual", "render", "pacote"]
    for ordem in (motion, avatar):
        pcts = [mensagens.PCT_ETAPA[e] for e in ordem]
        assert pcts == sorted(pcts) and pcts[0] > mensagens.PCT_REFERENCIA["aula"] and pcts[-1] < 100
