"""bot_youtube.previa: o primeiro minuto do vídeo em 720p, abaixo de 45 MB, para o sendVideo do Telegram (limite de 50 MB).

Pedido do Usuário (28/09/2026): a prévia é só 1 minuto, recortado do vídeo final (sem renderizar de novo); o YouTube
recebe o vídeo inteiro em 1080p."""
import json
import subprocess

from bot_youtube import mensagens, previa

LIMITE = 45 * 1024 * 1024


def _probe(mp4):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(mp4)], capture_output=True, text=True, check=True)
    dados = json.loads(r.stdout)
    return next(s for s in dados["streams"] if s["codec_type"] == "video"), float(dados["format"]["duration"])


def test_comando_corta_o_primeiro_minuto_e_cabe_em_45_mb():
    cmd = previa.comando("in.mp4", "out.mp4", 420)
    assert cmd[cmd.index("-t") + 1] == "60" and "scale=-2:720" in cmd
    kbps = previa.bitrate_kbps(60)
    assert cmd[cmd.index("-b:v") + 1] == f"{kbps}k" and (kbps + previa.AUDIO_KBPS) * 1000 / 8 * 60 < LIMITE
    assert previa.comando("in.mp4", "out.mp4", 40)[previa.comando("in.mp4", "out.mp4", 40).index("-t") + 1] == "40"


def test_previa_real_de_um_video_de_7_min_tem_1_min_em_720p(tmp_path):
    fonte = tmp_path / "fonte.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=5:duration=420",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=420", "-vf", "noise=alls=6:allf=t",
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-c:a", "aac", "-shortest", str(fonte)], check=True)
    saida = previa.gerar(fonte, tmp_path / "previa.mp4")
    video, duracao = _probe(saida)
    assert video["height"] == 720 and 59 <= duracao <= 60.5 and saida.stat().st_size < LIMITE


def test_texto_da_previa_avisa_que_e_o_primeiro_minuto():
    t = mensagens.texto_previa({"pedido": "y1", "horario": "2026-09-29T16:00:00-03:00", "envio_em": "2026-09-29T15:00:00-03:00"})
    assert "primeiro minuto" in t
