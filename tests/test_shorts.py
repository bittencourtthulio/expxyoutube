"""shorts.py: fila de reels, texto público, slots do dia, cota, journal e envio incerto."""
import json
import os
from datetime import datetime

import pytest

import shorts
import yt
from comum import SP

SLOTS = ["07:00", "09:30", "12:00", "15:00", "18:00", "21:00"]
AGORA = datetime(2026, 9, 29, 3, 0, tzinfo=SP)
VALIDO = {"largura": 1080, "altura": 1920, "duracao": 54.0, "audio": True}
CANAL = "UCcanalcerto"


class Req:
    def __init__(self, fn):
        self.fn = fn

    def execute(self):
        return self.fn()


class Rec:
    def __init__(self, **metodos):
        self.metodos = metodos

    def __getattr__(self, nome):
        return lambda **kw: Req(lambda: self.metodos[nome](**kw))


class DataFalsa:
    def __init__(self, canal=CANAL, videos=None):
        self.canal, self.db = canal, dict(videos or {})

    def channels(self):
        return Rec(list=lambda **kw: {"items": [{"id": self.canal, "contentDetails": {"relatedPlaylists": {"uploads": "UU"}}}]})

    def playlistItems(self):
        return Rec(list=lambda **kw: {"items": [{"contentDetails": {"videoId": v}} for v in self.db]})

    def videos(self):
        return Rec(list=lambda part, id, **kw: {"items": [self.db[v] for v in id.split(",") if v in self.db]})


def video_agendado(video_id, publish_at, canal=CANAL):
    return {"id": video_id, "status": {"privacyStatus": "private", "publishAt": publish_at},
            "snippet": {"channelId": canal, "title": "de fora"}}


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    monkeypatch.setattr(shorts, "ESTADO", tmp_path / "estado-shorts")
    pasta = tmp_path / "reels"
    pasta.mkdir()
    data = DataFalsa()
    cliente = yt.Cliente(data, None, raiz=tmp_path)
    cfg = shorts.Cfg(slots=SLOTS, pasta=pasta, canal_id=CANAL)
    subidos = []

    def enviar(cli, meta, publish_at):
        subidos.append({"chave": meta["chave"], "publish_at": publish_at, "titulo": meta["titulo"]})
        vid = f"vid{len(subidos)}"
        data.db[vid] = {"id": vid, "status": {"privacyStatus": "private", "publishAt": publish_at},
                        "snippet": {"channelId": CANAL, "title": meta["titulo"]}}
        return vid

    class Mundo:
        pass

    m = Mundo()
    m.pasta, m.cfg, m.data, m.cliente, m.subidos, m.enviar = pasta, cfg, data, cliente, subidos, enviar
    m.reel = lambda nome, tema=None, idade=0, legenda=None: _reel(pasta, nome, tema or f"tema numero {nome} com detalhes", idade, legenda)
    m.agendar = lambda **kw: shorts.agendar(cfg, agora=kw.pop("agora", AGORA), cliente=cliente, enviar=kw.pop("enviar", enviar),
                                            sonda=kw.pop("sonda", lambda mp4: dict(VALIDO)), **kw)
    return m


def _reel(pasta, nome, tema, idade, legenda):
    d = pasta / nome
    d.mkdir()
    (d / f"{nome}.mp4").write_bytes(b"x")
    (d / "legenda.txt").write_text(legenda or f"Comenta ARTE que eu te mando o {tema}.\n\n→ ponto um\n→ ponto dois\n\nComenta ARTE que eu te mando o link.\n\n#softwarehouse #ia\n",
                                   encoding="utf-8")
    alvo = 1_800_000_000 - idade
    os.utime(d / f"{nome}.mp4", (alvo, alvo))
    return d


# ---------- config ----------

def test_config_le_slots_do_ambiente_e_valida(tmp_path):
    vazio = tmp_path / "sem-chaves"
    cfg = shorts.carregar_config({"YT_SHORTS_SLOTS": "09:30, 07:00,07:00", "YT_COTA_DIA": "8000"}, vazio)
    assert cfg.slots == ["07:00", "09:30"] and cfg.cota_dia == 8000 and cfg.alias == "principal"
    with pytest.raises(shorts.ErroShorts, match="Falta YT_SHORTS_SLOTS"):
        shorts.carregar_config({}, vazio)
    with pytest.raises(shorts.ErroShorts, match="horário inválido: 25:00"):
        shorts.carregar_config({"YT_SHORTS_SLOTS": "07:00,25:00"}, vazio)


def test_config_ambiente_vence_arquivo(tmp_path):
    arquivo = tmp_path / "chaves"
    arquivo.write_text("YT_SHORTS_SLOTS=08:00\nYT_SHORTS_DIR=/tmp/reels-do-arquivo\n", encoding="utf-8")
    cfg = shorts.carregar_config({"YT_SHORTS_SLOTS": "10:00"}, arquivo)
    assert cfg.slots == ["10:00"] and str(cfg.pasta) == "/tmp/reels-do-arquivo"


# ---------- texto público ----------

def test_titulo_vem_do_tema_da_primeira_linha():
    legenda = "Comenta ARTE que eu te mando o Jaaz, o estúdio de design com IA que roda no seu computador.\n\n→ x"
    assert shorts.titulo_de(legenda) == "Jaaz, o estúdio de design com IA que roda no seu computador"


def test_titulo_tira_o_link_do_comeco_e_nao_termina_em_palavra_solta():
    assert shorts.titulo_de("Comenta FLOW que eu te mando o link do Flowise, o editor visual em que você monta agente de IA.\n") == \
        "Flowise, o editor visual em que você monta agente de IA"
    longo = ("Comenta X que eu te mando o roteador que tira do modelo caro a busca de arquivo e o resumo que o seu Claude Code faz o dia inteiro sozinho.")
    titulo = shorts.titulo_de(longo)
    assert len(titulo) <= 100 and titulo.split()[-1].lower() not in shorts.PALAVRAS_SOLTAS


def test_titulo_cai_para_a_primeira_frase_e_respeita_100_caracteres():
    legenda = "Comenta LINK que eu te mando o link.\n\n" + ("Palavra " * 30) + ".\n\n→ x"
    titulo = shorts.titulo_de(legenda)
    assert 0 < len(titulo) <= 100 and titulo.startswith("Palavra Palavra") and not titulo.endswith(" ")


def test_descricao_tira_o_comenta_do_instagram_e_poe_cta_e_shorts():
    legenda = "Comenta ARTE que eu te mando o Jaaz.\n\n→ um\n→ dois\n\nComenta ARTE que eu te mando o link.\n\n#a #b\n"
    d = shorts.descricao_de(legenda)
    assert "Comenta" not in d and "→ um" in d
    assert d.splitlines()[-1] == "#a #b #Shorts" and "https://example.com" in d


def test_recriacao_nunca_no_texto_publico():
    assert shorts.proibidos("Aula recriada", "ok") == ["título"]
    assert shorts.proibidos("ok", "Uma recriação") == ["descrição"]
    assert shorts.proibidos("ok", "tudo certo") == []


def test_validar_video_exige_vertical_curto_e_com_audio():
    shorts.validar_video(VALIDO)
    for ruim, trecho in (({**VALIDO, "largura": 1920, "altura": 1080}, "vertical"), ({**VALIDO, "duracao": 181}, "fora do limite"),
                         ({**VALIDO, "audio": False}, "sem áudio|não tem áudio")):
        with pytest.raises(ValueError, match=trecho):
            shorts.validar_video(ruim)


# ---------- fila ----------

def test_fila_do_mais_novo_ao_mais_antigo_com_exclusoes_e_sem_repetidos(mundo):
    mundo.reel("velho", idade=500)
    mundo.reel("novo", idade=0)
    mundo.reel("ignorar-exemplo", idade=100)
    shorts.ESTADO.mkdir(parents=True)
    (shorts.ESTADO / "config.json").write_text(json.dumps({"excluir_prefixos": ["ignorar-"]}))
    mundo.reel("copia-do-novo", idade=900, tema="tema numero novo com detalhes")
    (mundo.pasta / "sem-legenda").mkdir()
    (mundo.pasta / "sem-legenda" / "sem-legenda.mp4").write_bytes(b"x")
    assert [r["chave"] for r in shorts.fila(mundo.cfg)] == ["novo", "velho"]


def test_teto_e_exclusoes_vem_do_config_json(mundo):
    mundo.reel("a")
    (shorts.ESTADO).mkdir(parents=True)
    (shorts.ESTADO / "config.json").write_text(json.dumps({"excluir_prefixos": ["a"]}))
    assert shorts.fila(mundo.cfg) == []


# ---------- agendar ----------

def test_agenda_seis_reels_nos_seis_slots_do_dia_em_utc(mundo):
    for i in range(8):
        mundo.reel(f"r{i}", idade=i)
    relato = mundo.agendar()
    assert len(relato["agendados"]) == 6 and "erro" not in relato and relato["na_fila"] == 8
    assert [s["chave"] for s in mundo.subidos] == [f"r{i}" for i in range(6)]
    assert [s["publish_at"] for s in mundo.subidos][0] == "2026-09-29T10:00:00Z"     # 07:00 em São Paulo
    assert [s["publish_at"] for s in mundo.subidos][-1] == "2026-09-30T00:00:00Z"    # 21:00 em São Paulo
    assert [e["etapa"] for e in shorts.eventos()].count("agendado") == 6


def test_rodar_de_novo_no_mesmo_dia_nao_sobe_nada(mundo):
    for i in range(8):
        mundo.reel(f"r{i}", idade=i)
    mundo.agendar()
    mundo.data.db.clear()                       # a listagem do canal ainda não mostra os vídeos novos: o journal segura
    relato = mundo.agendar()
    assert relato["agendados"] == [] and len(mundo.subidos) == 6


def test_slot_ocupado_no_canal_e_slot_no_passado_ficam_de_fora(mundo):
    for i in range(6):
        mundo.reel(f"r{i}", idade=i)
    mundo.data.db["aula"] = video_agendado("aula", "2026-09-29T15:00:00Z")           # 12:00 em São Paulo
    relato = mundo.agendar(agora=datetime(2026, 9, 29, 8, 30, tzinfo=SP))            # piso 10:00 (90 min)
    assert [a["horario"][11:16] for a in relato["agendados"]] == ["15:00", "18:00", "21:00"]


def test_cota_limita_quantos_sobem(mundo):
    for i in range(8):
        mundo.reel(f"r{i}", idade=i)
    mundo.cfg.cota_dia = 5000
    relato = mundo.agendar()
    assert len(mundo.subidos) == 3 and any("cota" in a for a in relato["avisos"])


def test_upload_conta_1600_unidades_na_cota(mundo):
    mundo.reel("r0")
    mundo.agendar()
    cota = json.loads((mundo.cliente.raiz / "estado" / "cota.json").read_text())
    assert sum(v["data"] for v in cota.values()) >= shorts.CUSTO_UPLOAD


def test_teto_total_do_config_json(mundo):
    for i in range(8):
        mundo.reel(f"r{i}", idade=i)
    shorts.ESTADO.mkdir(parents=True)
    (shorts.ESTADO / "config.json").write_text(json.dumps({"max_total": 3}))
    relato = mundo.agendar()
    assert len(mundo.subidos) == 3 and any("teto" in a for a in relato["avisos"])
    assert mundo.agendar(dia=datetime(2026, 9, 30).date())["agendados"] == []


def test_simular_nao_sobe_nem_grava(mundo):
    mundo.reel("r0")
    relato = mundo.agendar(simular=True)
    assert len(relato["agendados"]) == 1 and mundo.subidos == [] and shorts.eventos() == []


def test_reel_invalido_e_pulado_e_o_proximo_ocupa_o_slot(mundo):
    mundo.reel("ruim", idade=0)
    mundo.reel("bom", idade=10)
    relato = mundo.agendar(sonda=lambda mp4: {**VALIDO, "largura": 1920, "altura": 1080} if "ruim" in str(mp4) else dict(VALIDO))
    assert [s["chave"] for s in mundo.subidos] == ["bom"]
    assert relato["pulados"][0]["chave"] == "ruim" and shorts.situacao()["ruim"]["etapa"] == "falhou"
    assert "ruim" not in [r["chave"] for r in shorts.fila(mundo.cfg)]


def test_recriacao_no_texto_bloqueia_o_reel(mundo):
    mundo.reel("r0", tema="aula recriada do zero")
    relato = mundo.agendar()
    assert mundo.subidos == [] and "recria" in relato["pulados"][0]["motivo"]


def test_canal_errado_aborta_sem_escrever(mundo):
    mundo.reel("r0")
    mundo.data.canal = "UCoutro"
    with pytest.raises(shorts.ErroShorts, match="canal autenticado difere"):
        mundo.agendar()
    assert mundo.subidos == [] and shorts.eventos() == []


def test_cota_estourada_para_e_devolve_o_reel_a_fila(mundo):
    mundo.reel("r0")

    def cheia(cli, meta, publish_at):
        raise yt.ErroAPI(403, "quotaExceeded", "sem cota")
    relato = mundo.agendar(enviar=cheia)
    assert relato["agendados"] == [] and "erro" not in relato and any("quotaExceeded" in a for a in relato["avisos"])
    assert [r["chave"] for r in shorts.fila(mundo.cfg)] == ["r0"]


def test_login_expirado_para_com_erro_e_devolve_a_fila(mundo):
    mundo.reel("r0")

    def sem_login(cli, meta, publish_at):
        raise yt.ErroAuth("credencial expirada; refaça o login: .venv/bin/python auth.py principal")
    relato = mundo.agendar(enviar=sem_login)
    assert "refaça o login" in relato["erro"] and [r["chave"] for r in shorts.fila(mundo.cfg)] == ["r0"]


def test_erro_4xx_marca_falhou_e_segue_para_o_proximo(mundo):
    mundo.reel("r0", idade=0)
    mundo.reel("r1", idade=10)

    def recusa_r0(cli, meta, publish_at):
        if meta["chave"] == "r0":
            raise yt.ErroAPI(400, "invalidTitle", "título inválido")
        return mundo.enviar(cli, meta, publish_at)
    mundo.agendar(enviar=recusa_r0)
    assert shorts.situacao()["r0"]["etapa"] == "falhou" and [s["chave"] for s in mundo.subidos] == ["r1"]


def test_envio_incerto_trava_a_fila_ate_reconciliar(mundo):
    mundo.reel("r0", idade=0)
    mundo.reel("r1", idade=10)

    def cai(cli, meta, publish_at):
        raise ConnectionError("caiu no meio do upload")
    relato = mundo.agendar(enviar=cai)
    assert "incerto" in relato["erro"] and shorts.situacao()["r0"]["etapa"] == "enviando"
    with pytest.raises(shorts.ErroShorts, match="resultado incerto"):
        mundo.agendar()
    assert mundo.subidos == []
    shorts.reconciliar(mundo.cfg, "r0", nao_subiu=True, cliente=mundo.cliente)
    assert [r["chave"] for r in shorts.fila(mundo.cfg)] == ["r0", "r1"]
    assert len(mundo.agendar()["agendados"]) == 2


def test_reconciliar_com_video_id_marca_agendado(mundo):
    mundo.reel("r0")
    mundo.agendar(enviar=lambda *a: (_ for _ in ()).throw(TimeoutError("x")))
    mundo.data.db["vidX"] = video_agendado("vidX", "2026-09-29T10:00:00Z")
    out = shorts.reconciliar(mundo.cfg, "r0", video_id="vidX", cliente=mundo.cliente)
    assert out["resultado"] == "agendado" and shorts.situacao()["r0"]["etapa"] == "agendado"
    mundo.data.db["vidY"] = video_agendado("vidY", "2026-09-29T10:00:00Z", canal="UCoutro")
    shorts.registrar("r9", "enviando")
    with pytest.raises(shorts.ErroShorts, match="não está no canal autorizado"):
        shorts.reconciliar(mundo.cfg, "r9", video_id="vidY", cliente=mundo.cliente)


def test_agendamento_nao_confirmado_trava_para_reconciliar(mundo):
    mundo.reel("r0")

    def sem_publish_at(cli, meta, publish_at):
        mundo.data.db["vidZ"] = {"id": "vidZ", "status": {"privacyStatus": "private"}, "snippet": {"channelId": CANAL, "title": "x"}}
        return "vidZ"
    relato = mundo.agendar(enviar=sem_publish_at)
    assert "não foi confirmado" in relato["erro"] and shorts.situacao()["r0"]["etapa"] == "verificar"


def test_liberar_e_excluir(mundo):
    mundo.reel("r0")
    shorts.excluir("r0")
    assert shorts.fila(mundo.cfg) == []
    shorts.liberar("r0")
    assert [r["chave"] for r in shorts.fila(mundo.cfg)] == ["r0"]
    with pytest.raises(shorts.ErroShorts):
        shorts.liberar("r0")


def test_main_status_e_erro_de_config(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(shorts, "ESTADO", tmp_path / "e")
    monkeypatch.setattr(shorts, "carregar_config", lambda: (_ for _ in ()).throw(shorts.ErroShorts("Falta YT_SHORTS_SLOTS")))
    assert shorts.main(["status"]) == 1
    assert json.loads(capsys.readouterr().out) == {"ok": False, "error": "Falta YT_SHORTS_SLOTS"}
