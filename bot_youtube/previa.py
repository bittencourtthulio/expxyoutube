"""Prévia do vídeo para o Telegram: o primeiro minuto, recortado do vídeo final (sem renderizar de novo), em 720p e
abaixo de 45 MB (o sendVideo aceita até 50 MB). O YouTube recebe o vídeo inteiro em 1080p (D-12).
Só 1 minuto: pedido do Usuário em 28/09/2026 (prévia mais rápida de gerar e de enviar)."""
import json
import subprocess
from pathlib import Path

ALVO_BYTES = 45 * 1024 * 1024
AUDIO_KBPS = 128
MARGEM = 0.9
DURACAO_PREVIA = 60


def bitrate_kbps(duracao):
    total_kbps = ALVO_BYTES * 8 / 1000 / max(duracao, 1) * MARGEM
    return max(int(total_kbps - AUDIO_KBPS), 150)


def comando(mp4, destino, duracao):
    trecho = int(min(duracao, DURACAO_PREVIA))
    kbps = bitrate_kbps(trecho)
    return ["ffmpeg", "-v", "error", "-y", "-i", str(mp4), "-t", str(trecho), "-vf", "scale=-2:720", "-c:v", "libx264", "-preset", "veryfast",
            "-b:v", f"{kbps}k", "-maxrate", f"{kbps}k", "-bufsize", f"{kbps * 2}k", "-c:a", "aac", "-b:a", f"{AUDIO_KBPS}k",
            "-movflags", "+faststart", str(destino)]


def duracao(mp4):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(mp4)],
                       capture_output=True, text=True, check=True)
    return float(json.loads(r.stdout)["format"]["duration"])


def gerar(mp4, destino):
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(comando(mp4, destino, duracao(mp4)), check=True, capture_output=True, text=True, timeout=3600)
    if destino.stat().st_size >= ALVO_BYTES:
        raise RuntimeError(f"prévia com {destino.stat().st_size} bytes passou de 45 MB")
    return destino
