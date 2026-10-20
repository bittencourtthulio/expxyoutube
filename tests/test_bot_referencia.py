"""bot_youtube.referencia: baixar (yt-dlp), transcrever (whisper local) e tirar quadros (ffmpeg) do vídeo de referência."""
import json
import shutil
import subprocess

import pytest

from bot_youtube import executar, referencia
from tests.falsos_bot import roteiro_bin


def _rodar_com(env):
    return lambda cmd, timeout=None, cwd=None: executar.rodar(cmd, timeout=timeout, cwd=cwd, env=env)


# --- T-03.05 baixar --------------------------------------------------------------------------------

def test_baixar_grava_video_e_origem(tmp_path):
    pasta = tmp_path / "pedido"
    info = {"title": "Claude Code em 10 minutos", "channel": "Canal X", "duration": 612, "webpage_url": "https://youtu.be/x"}
    env = roteiro_bin(tmp_path, "yt-dlp", arquivos={"{arg:-o}": "mp4", str(pasta / "referencia/video.info.json"): json.dumps(info)})
    origem = referencia.baixar("https://youtu.be/x", pasta, timeout=60, executar=_rodar_com(env))
    assert (pasta / "referencia/video.mp4").exists()
    gravada = json.loads((pasta / "origem.json").read_text())
    assert gravada == origem and origem["duracao"] == 612 and origem["titulo"] == "Claude Code em 10 minutos"
    assert origem["url"] == "https://youtu.be/x" and origem["canal"] == "Canal X"


def test_403_da_a_dica_de_atualizar(tmp_path):
    env = roteiro_bin(tmp_path, "yt-dlp", stderr="ERROR: unable to download video data: HTTP Error 403: Forbidden", codigo=1)
    with pytest.raises(referencia.Erro) as e:
        referencia.baixar("https://youtu.be/x", tmp_path / "pedido", timeout=60, executar=_rodar_com(env))
    assert "pip install -U yt-dlp" in str(e.value)


# --- T-03.06 transcrever ---------------------------------------------------------------------------

def test_transcrever_com_whisper_falso(tmp_path):
    pasta = tmp_path / "pedido"
    (pasta / "referencia").mkdir(parents=True)
    (pasta / "referencia/video.mp4").write_text("x")
    saida = {"text": " Olá  pessoal.\n\nHoje   vamos ver agentes. ", "language": "pt",
             "segments": [{"start": 0.0, "end": 2.0, "text": " Olá pessoal."}, {"start": 2.0, "end": 4.0, "text": " Hoje vamos ver agentes."}]}
    env = roteiro_bin(tmp_path, "whisper", arquivos={"{arg:--output_dir}/video.json": json.dumps(saida)})
    r = referencia.transcrever(pasta, timeout=60, executar=_rodar_com(env))
    assert (pasta / "referencia/transcricao.txt").read_text() == "Olá pessoal. Hoje vamos ver agentes."
    segs = json.loads((pasta / "referencia/transcricao.json").read_text())
    assert segs["idioma"] == "pt" and len(segs["segmentos"]) == 2 and r["idioma"] == "pt"


@pytest.mark.skipif(not (shutil.which("say") and shutil.which("whisper")), reason="precisa de say e whisper")
def test_transcrever_real_com_say(tmp_path):
    pasta = tmp_path / "pedido"
    (pasta / "referencia").mkdir(parents=True)
    aiff = tmp_path / "fala.aiff"
    subprocess.run(["say", "-v", "Flo", "-o", str(aiff), "Olá pessoal, hoje nós vamos aprender como funciona o mundo das aulas de inteligência artificial, passo a passo, com calma."], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(aiff), "-f", "lavfi", "-i", "color=c=black:s=320x240:d=12",
                    "-shortest", str(pasta / "referencia/video.mp4")], check=True)
    referencia.transcrever(pasta, timeout=600, modelo="small")
    assert "mundo" in (pasta / "referencia/transcricao.txt").read_text().lower()


# --- T-03.07 quadros -------------------------------------------------------------------------------

def test_quantidade_de_quadros():
    assert referencia.quantidade_quadros(95) == 4 and referencia.quantidade_quadros(90) == 3


def test_quadros_reais_de_90s(tmp_path):
    pasta = tmp_path / "pedido"
    (pasta / "referencia").mkdir(parents=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=5:duration=90",
                    str(pasta / "referencia/video.mp4")], check=True)
    quadros = referencia.quadros(pasta)
    assert len(quadros) == 3 and all(q.suffix == ".jpg" and q.stat().st_size > 0 for q in quadros)
    assert sorted(p.name for p in (pasta / "referencia/quadros").iterdir()) == ["000.jpg", "030.jpg", "060.jpg"]


# --- legenda do YouTube antes do whisper (pedido do Usuário, 28/09/2026) ------------------------------

JSON3 = {"events": [
    {"tStartMs": 0, "dDurationMs": 2000, "segs": [{"utf8": "Olá"}, {"utf8": " pessoal"}]},
    {"tStartMs": 1000, "dDurationMs": 10, "aAppend": 1, "segs": [{"utf8": "\n"}]},
    {"tStartMs": 2000, "dDurationMs": 3000, "segs": [{"utf8": "hoje vamos orquestrar agentes"}]},
]}


def _pasta_com_info(tmp_path, info):
    pasta = tmp_path / "pedido"
    (pasta / "referencia").mkdir(parents=True)
    (pasta / "referencia/video.mp4").write_text("x")
    (pasta / "referencia/video.info.json").write_text(json.dumps(info))
    return pasta


def test_usa_a_legenda_original_do_youtube_e_nao_chama_o_whisper(tmp_path):
    from tests.falsos_bot import chamadas_bin
    pasta = _pasta_com_info(tmp_path, {"language": "pt-BR", "subtitles": {}, "automatic_captions": {"en": [{}], "pt": [{}], "pt-orig": [{}]}})
    roteiro = roteiro_bin(tmp_path, "yt-dlp", arquivos={"{arg:-o}.pt-orig.json3": json.dumps(JSON3)})
    r = referencia.transcrever(pasta, timeout=60, executar=_rodar_com(roteiro), url="https://youtu.be/x")
    assert r["fonte"] == "youtube:pt-orig" and r["idioma"] == "pt"
    assert (pasta / "referencia/transcricao.txt").read_text() == "Olá pessoal hoje vamos orquestrar agentes"
    segs = json.loads((pasta / "referencia/transcricao.json").read_text())["segmentos"]
    assert segs[0] == {"inicio": 0.0, "fim": 2.0, "texto": "Olá pessoal"} and len(segs) == 2
    chamadas = chamadas_bin(tmp_path)
    assert [c["bin"] for c in chamadas] == ["yt-dlp"]
    argv = chamadas[0]["argv"]
    assert "--skip-download" in argv and argv[argv.index("--sub-langs") + 1] == "pt-orig"


def test_legenda_manual_vence_a_automatica(tmp_path):
    pasta = _pasta_com_info(tmp_path, {"language": "en", "subtitles": {"en": [{}]}, "automatic_captions": {"en-orig": [{}]}})
    assert referencia.escolher_legenda(json.loads((pasta / "referencia/video.info.json").read_text())) == ("en", "manual")


def test_sem_legenda_cai_no_whisper(tmp_path):
    from tests.falsos_bot import chamadas_bin
    pasta = _pasta_com_info(tmp_path, {"language": "pt", "subtitles": {}, "automatic_captions": {}})
    saida = {"text": "Oi", "language": "pt", "segments": [{"start": 0, "end": 1, "text": "Oi"}]}
    roteiro = roteiro_bin(tmp_path, "whisper", arquivos={"{arg:--output_dir}/video.json": json.dumps(saida)})
    r = referencia.transcrever(pasta, timeout=60, executar=_rodar_com(roteiro), url="https://youtu.be/x")
    assert r["fonte"] == "whisper" and [c["bin"] for c in chamadas_bin(tmp_path)] == ["whisper"]


def test_usa_a_url_da_legenda_que_veio_no_download_sem_chamar_o_yt_dlp(tmp_path):
    from tests.falsos_bot import chamadas_bin
    pasta = _pasta_com_info(tmp_path, {"language": "pt-BR", "subtitles": {},
                                       "automatic_captions": {"pt-orig": [{"ext": "vtt", "url": "http://legenda/vtt"},
                                                                          {"ext": "json3", "url": "http://legenda/json3"}]}})
    pedidas = []
    roteiro = roteiro_bin(tmp_path, "yt-dlp")
    r = referencia.transcrever(pasta, timeout=60, executar=_rodar_com(roteiro), url="https://youtu.be/x",
                               http_get=lambda url, timeout=None: pedidas.append(url) or json.dumps(JSON3).encode())
    assert pedidas == ["http://legenda/json3"] and r["fonte"] == "youtube:pt-orig"
    assert chamadas_bin(tmp_path) == []


def test_url_da_legenda_expirada_cai_no_yt_dlp(tmp_path):
    from tests.falsos_bot import chamadas_bin
    pasta = _pasta_com_info(tmp_path, {"language": "pt", "automatic_captions": {"pt-orig": [{"ext": "json3", "url": "http://legenda/json3"}]}})

    def expirada(url, timeout=None):
        raise OSError("HTTP 403")
    roteiro = roteiro_bin(tmp_path, "yt-dlp", arquivos={"{arg:-o}.pt-orig.json3": json.dumps(JSON3)})
    r = referencia.transcrever(pasta, timeout=60, executar=_rodar_com(roteiro), url="https://youtu.be/x", http_get=expirada)
    assert r["fonte"] == "youtube:pt-orig" and [c["bin"] for c in chamadas_bin(tmp_path)] == ["yt-dlp"]
