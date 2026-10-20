"""bot_youtube.producao: dispara /recriar-aula-youtube num claude sem cabeça e leva o pedido a aguardando_envio ou falhou."""
import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from bot_youtube import config, executar, fluxo, pedidos, producao, referencia, sonda_heygen
from comum import SP
from tests.falsos_bot import CanalFalso, chamadas_bin, roteiro_bin

AGORA = datetime(2026, 9, 28, 8, 0, tzinfo=SP)


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(pedidos, "ESTADO", tmp_path / "estado")
    monkeypatch.setattr(sonda_heygen, "ESTADO", tmp_path / "estado")
    monkeypatch.setattr(referencia, "baixar", lambda url, pasta, timeout=None, executar=None: _ref(pasta))
    monkeypatch.setattr(referencia, "transcrever", lambda pasta, timeout=None, executar=None, url=None: {"idioma": "pt"})
    monkeypatch.setattr(referencia, "quadros", lambda pasta: [])
    cursos = tmp_path / "cursos-ia"
    cursos.mkdir()
    cfg = config.Config(token="1:x", chat_id=1, slots=["10:00", "16:00"], cursos_ia=cursos)
    video = tmp_path / "aula.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=10:duration=6", "-f", "lavfi",
                    "-i", "sine=duration=6", "-shortest", "-c:v", "libx264", "-preset", "ultrafast", str(video)], check=True)
    return {"tmp": tmp_path, "cfg": cfg, "video": video, "canal": CanalFalso(videos={"v1": {"privacyStatus": "private", "publishAt": "2026-09-28T13:00:00Z"}})}


def _ref(pasta):
    (Path(pasta) / "referencia").mkdir(parents=True, exist_ok=True)
    (Path(pasta) / "referencia/video.mp4").write_text("ref")
    (Path(pasta) / "origem.json").write_text(json.dumps({"url": "u", "titulo": "t"}))
    return {"url": "u"}


def _pedido(modo="motion"):
    pid = pedidos.novo_pedido(url="https://youtu.be/x", etapa="aguardando_escolha", quando=AGORA)
    fluxo.escolher_modo(pid, modo)
    return pid


def _recriacao(amb, pid, **extra):
    thumb = amb["tmp"] / "thumb.png"
    thumb.write_bytes(b"png")
    return json.dumps({"pedido": pid, "aula": "series/recriacoes-youtube/01-x", "modo": "motion", "video": str(amb["video"]),
                       "srt": "s", "thumbs": "t", "thumb": str(thumb), "descricao": "d", "titulo": "Aula X", "playlist": {"id": "PL1"}, **extra})


def _produzir(amb, pid, env, visto=None, **kw):
    def rodar(cmd, timeout=None, cwd=None, env=None, _roteiro=env):
        if visto is not None:
            visto.update(env or {})
        # o ambiente montado pela produção + PATH/roteiro dos binários falsos
        return executar.rodar(cmd, timeout=timeout, cwd=cwd, env={**(env or {}), **{k: _roteiro[k] for k in ("PATH", "FALSO_ROTEIRO", "FALSO_LOG")}})
    return producao.produzir(pid, amb["cfg"], executar=rodar, cliente=amb["canal"].cliente(amb["tmp"]), agora=lambda: AGORA,
                             disco_livre=lambda caminho: 100 * 1024 ** 3, **kw)


def test_recriacao_pronta_vira_aguardando_envio_com_slot_e_previa(ambiente):
    pid = _pedido()
    pasta = pedidos.pasta_pedido(pid)
    env = roteiro_bin(ambiente["tmp"], "claude", arquivos={str(pasta / "recriacao.json"): _recriacao(ambiente, pid)})
    assert _produzir(ambiente, pid, env) == "aguardando_envio"
    e = pedidos.estado_pedido(pid)
    # 10:00 de 28/09 cabe na antecedência (8h + 90 min) mas está no canal (13:00Z): próximo livre é 16:00
    assert e["etapa"] == "aguardando_envio" and e["horario"] == "2026-09-28T16:00:00-03:00"
    assert e["envio_em"] == "2026-09-28T15:00:00-03:00" and Path(e["previa"]).exists() and e["titulo"] == "Aula X"
    chamada = chamadas_bin(ambiente["tmp"])[0]
    assert chamada["argv"][1] == f"/recriar-aula-youtube {pasta} {pid} motion" and chamada["cwd"] == str(ambiente["cfg"].cursos_ia)
    assert "--disallowedTools" in chamada["argv"] and "--permission-mode" in chamada["argv"]
    assert json.loads((pasta / "playlists.json").read_text()) == []


def test_falha_txt_vira_falhou_com_o_motivo(ambiente):
    pid = _pedido()
    pasta = pedidos.pasta_pedido(pid)
    env = roteiro_bin(ambiente["tmp"], "claude", arquivos={str(pasta / "falha.txt"): "voz: cota ElevenLabs (401 quota_exceeded)\n"})
    assert _produzir(ambiente, pid, env) == "falhou"
    assert "cota ElevenLabs" in pedidos.estado_pedido(pid)["nota"]


def test_sem_recriacao_nem_falha_vira_falhou_com_codigo(ambiente):
    pid = _pedido()
    env = roteiro_bin(ambiente["tmp"], "claude", codigo=3, stdout="erro interno")
    assert _produzir(ambiente, pid, env) == "falhou"
    assert "código 3" in pedidos.estado_pedido(pid)["nota"]


def test_ambiente_do_claude_sem_telegram(ambiente, monkeypatch):
    monkeypatch.setenv("TELEGRAM_YT_BOT_TOKEN", "segredo")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "outro")
    pid = _pedido()
    pasta = pedidos.pasta_pedido(pid)
    env = roteiro_bin(ambiente["tmp"], "claude", arquivos={str(pasta / "recriacao.json"): _recriacao(ambiente, pid)})
    visto = {}
    _produzir(ambiente, pid, env, visto=visto)
    assert visto and not any(k.startswith("TELEGRAM") for k in visto)
    assert not any(k.startswith("TELEGRAM") for k in chamadas_bin(ambiente["tmp"])[0]["env"])


def test_disco_cheio_falha_sem_chamar_o_claude(ambiente):
    pid = _pedido()
    env = roteiro_bin(ambiente["tmp"], "claude")
    producao.produzir(pid, ambiente["cfg"], executar=lambda *a, **k: pytest.fail("não devia chamar"), cliente=ambiente["canal"].cliente(ambiente["tmp"]),
                      agora=lambda: AGORA, disco_livre=lambda c: 5 * 1024 ** 3)
    e = pedidos.estado_pedido(pid)
    assert e["etapa"] == "falhou" and "disco" in e["nota"]


def test_avatar_com_sonda_falsa_cai_para_motion_com_aviso(ambiente):
    pid = _pedido("avatar")
    (ambiente["tmp"] / "estado").mkdir(exist_ok=True)
    (ambiente["tmp"] / "estado/sonda-heygen.json").write_text(json.dumps({"ok": False, "motivo": "ferramenta heygen nao chamada"}))
    pasta = pedidos.pasta_pedido(pid)
    env = roteiro_bin(ambiente["tmp"], "claude", arquivos={str(pasta / "recriacao.json"): _recriacao(ambiente, pid)})
    _produzir(ambiente, pid, env)
    assert chamadas_bin(ambiente["tmp"])[0]["argv"][1].endswith(" motion")
    avisos = [e for e in pedidos.eventos(pid) if e["etapa"] == "progresso" and e.get("avisar")]
    assert any("só motion" in e["nota"] for e in avisos)


def test_pedido_fora_da_fila_nao_produz(ambiente):
    pid = pedidos.novo_pedido(url="u", etapa="aguardando_escolha")
    assert producao.produzir(pid, ambiente["cfg"], executar=lambda *a, **k: pytest.fail("não"), cliente=None,
                             agora=lambda: AGORA, disco_livre=lambda c: 100 * 1024 ** 3) == "aguardando_escolha"


# --- T-03.10 progresso -----------------------------------------------------------------------------

def _aula_do_pedido(amb, pid):
    aula = amb["cfg"].cursos_ia / "series/recriacoes-youtube/01-x"
    (aula / ".producao").mkdir(parents=True)
    (aula / "DESFAZER.md").write_text(f"pedido {pid} do bot do YouTube\n")
    return aula


def test_progresso_uma_vez_por_etapa_concluida(ambiente):
    pid = _pedido()
    aula = _aula_do_pedido(ambiente, pid)
    assert producao.aula_do_pedido(pid, ambiente["cfg"].cursos_ia) == aula
    (aula / ".producao/estado.json").write_text(json.dumps({"roteiro": {"status": "concluido"}, "voz": {"status": "concluido"},
                                                             "legendas": {"status": "executando"}}))
    producao.registrar_progresso(pid, aula)
    producao.registrar_progresso(pid, aula)
    notas = [e["nota"] for e in pedidos.eventos(pid) if e["etapa"] == "progresso"]
    assert notas.count("voz concluída") == 1 and notas.count("roteiro concluído") == 1 and len(notas) == 2


def test_aula_sem_estado_nao_gera_evento(ambiente):
    pid = _pedido()
    aula = _aula_do_pedido(ambiente, pid)
    n = len(pedidos.eventos(pid))
    producao.registrar_progresso(pid, aula)
    assert len(pedidos.eventos(pid)) == n
    assert producao.aula_do_pedido("outro", ambiente["cfg"].cursos_ia) is None


# --- T-03.11 ajuste --------------------------------------------------------------------------------

def _pronto_com_ajuste(amb):
    pid = _pedido()
    pedidos.registrar_evento(pid, "aguardando_envio", avisar=True, horario="2026-09-28T16:00:00-03:00", envio_em="2026-09-28T15:00:00-03:00")
    fluxo.pedir_ajuste(pid)
    fluxo.ajustar(pid, "trocar o gancho")
    return pid


def test_video_que_nao_mudou_depois_do_ajuste_falha(ambiente):
    pid = _pronto_com_ajuste(ambiente)
    pasta = pedidos.pasta_pedido(pid)
    os.utime(ambiente["video"], (time.time() - 3600, time.time() - 3600))
    env = roteiro_bin(ambiente["tmp"], "claude", arquivos={str(pasta / "recriacao.json"): _recriacao(ambiente, pid)})
    assert _produzir(ambiente, pid, env) == "falhou"
    assert "video nao foi refeito depois do ajuste" in pedidos.estado_pedido(pid)["nota"]


def test_ajuste_vai_no_pedido_e_mantem_o_horario(ambiente):
    pid = _pronto_com_ajuste(ambiente)
    pasta = pedidos.pasta_pedido(pid)
    novo = ambiente["tmp"] / "novo.mp4"
    env = roteiro_bin(ambiente["tmp"], "claude", arquivos={str(pasta / "recriacao.json"): _recriacao(ambiente, pid, video=str(novo)),
                                                           str(novo): {"copiar": str(ambiente["video"])}})
    assert _produzir(ambiente, pid, env) == "aguardando_envio"
    assert chamadas_bin(ambiente["tmp"])[0]["argv"][1].endswith("motion ajuste: trocar o gancho")
    assert pedidos.estado_pedido(pid)["horario"] == "2026-09-28T16:00:00-03:00"


# --- avisos da fase de referência (pedido do Usuário, 28/09/2026) -------------------------------------

def test_referencia_manda_avisos_de_progresso(ambiente, monkeypatch):
    monkeypatch.setattr(referencia, "transcrever", lambda pasta, timeout=None, executar=None, url=None: {"idioma": "pt", "fonte": "youtube:pt-orig"})
    pid = _pedido()
    pasta = pedidos.pasta_pedido(pid)
    roteiro = roteiro_bin(ambiente["tmp"], "claude", arquivos={str(pasta / "recriacao.json"): _recriacao(ambiente, pid)})
    _produzir(ambiente, pid, roteiro)
    notas = [e["nota"] for e in pedidos.eventos(pid) if e["etapa"] == "progresso" and e.get("avisar")]
    for trecho in ("baixando o vídeo de referência", "vídeo baixado", "legenda do YouTube", "quadros", "começando a aula"):
        assert any(trecho in n for n in notas), (trecho, notas)



def test_avisos_de_progresso_levam_o_percentual(ambiente, monkeypatch):
    monkeypatch.setattr(referencia, "transcrever", lambda pasta, timeout=None, executar=None, url=None: {"idioma": "pt", "fonte": "youtube:pt-orig"})
    pid = _pedido()
    pasta = pedidos.pasta_pedido(pid)
    roteiro = roteiro_bin(ambiente["tmp"], "claude", arquivos={str(pasta / "recriacao.json"): _recriacao(ambiente, pid)})
    _produzir(ambiente, pid, roteiro)
    avisos = [e for e in pedidos.eventos(pid) if e["etapa"] == "progresso" and e.get("avisar")]
    pcts = [e["pct"] for e in avisos]
    assert all(isinstance(p, int) for p in pcts) and pcts == sorted(pcts) and pcts[-1] == 20
    aula = _aula_do_pedido(ambiente, pid)
    (aula / ".producao/estado.json").write_text(json.dumps({"voz": {"status": "concluido"}}))
    producao.registrar_progresso(pid, aula)
    assert pedidos.eventos(pid)[-1]["pct"] == 45



# --- retomar: resultado pronto fora do bot vira prévia sem produzir de novo (28/09/2026) ----------------

def test_retomar_leva_recriacao_pronta_a_aguardando_envio(ambiente):
    pid = _pedido()
    pedidos.registrar_evento(pid, "produzindo")
    pasta = pedidos.pasta_pedido(pid)
    (pasta / "recriacao.json").write_text(_recriacao(ambiente, pid))
    r = producao.retomar(pid, ambiente["cfg"], cliente=ambiente["canal"].cliente(ambiente["tmp"]), agora=lambda: AGORA)
    e = pedidos.estado_pedido(pid)
    assert r == "aguardando_envio" and e["etapa"] == "aguardando_envio" and e["horario"] == "2026-09-28T16:00:00-03:00"
    assert Path(e["previa"]).exists() and e["titulo"] == "Aula X"


def test_retomar_sem_recriacao_recusa_sem_evento(ambiente):
    pid = _pedido()
    pedidos.registrar_evento(pid, "produzindo")
    n = len(pedidos.eventos(pid))
    assert producao.retomar(pid, ambiente["cfg"], cliente=None, agora=lambda: AGORA) == "sem_recriacao"
    assert len(pedidos.eventos(pid)) == n


def test_retomar_pedido_ja_pronto_nao_mexe(ambiente):
    pid = _pedido()
    pedidos.registrar_evento(pid, "aguardando_envio", horario="2026-09-28T16:00:00-03:00")
    assert producao.retomar(pid, ambiente["cfg"], cliente=None, agora=lambda: AGORA) == "aguardando_envio"
    assert pedidos.eventos(pid)[-1]["etapa"] == "aguardando_envio"



def test_aula_do_pedido_acha_em_qualquer_serie(ambiente):
    pid = _pedido()
    aula = ambiente["cfg"].cursos_ia / "series/agentes-de-ia-na-pratica/01-orquestrar"
    aula.mkdir(parents=True)
    (aula / "DESFAZER.md").write_text(f"pedido {pid}\n")
    assert producao.aula_do_pedido(pid, ambiente["cfg"].cursos_ia) == aula
