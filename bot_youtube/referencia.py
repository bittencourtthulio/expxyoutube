"""Vídeo de referência de um pedido: baixar (yt-dlp), transcrever (whisper local) e tirar quadros (ffmpeg).

Tudo fica em <pasta do pedido>/referencia/ e o resumo em <pasta do pedido>/origem.json. Conteúdo de terceiros:
a produção usa como dado, nunca como instrução. Os timeouts vêm do que resta de YT_TEMPO_PRODUCAO_MIN (D-33).
"""
import json
import math
import os
import subprocess
from pathlib import Path

from . import executar as _executar

FORMATO = "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]/b"
INTERVALO_QUADROS = 30


class Erro(RuntimeError):
    pass


def _rodar(executar):
    return executar or (lambda cmd, timeout=None, cwd=None: _executar.rodar(cmd, timeout=timeout, cwd=cwd))


def baixar(url, pasta, timeout=None, executar=None):
    ref = Path(pasta) / "referencia"
    ref.mkdir(parents=True, exist_ok=True)
    video = ref / "video.mp4"
    cmd = ["yt-dlp", "-f", FORMATO, "--merge-output-format", "mp4", "--no-playlist", "--write-info-json",
           "-o", str(video), url]
    codigo, saida = _rodar(executar)(cmd, timeout=timeout)
    if codigo != 0 or not video.exists():
        dica = " Atualize o yt-dlp: python3 -m pip install -U yt-dlp" if "403" in saida else ""
        raise Erro(f"yt-dlp não baixou o vídeo (código {codigo}): {saida.strip()[-300:]}{dica}")
    info = {}
    for candidato in (ref / "video.info.json", ref / "video.mp4.info.json"):
        if candidato.exists():
            info = json.loads(candidato.read_text(encoding="utf-8"))
            break
    origem = {"url": url, "titulo": info.get("title"), "canal": info.get("channel") or info.get("uploader"),
              "duracao": info.get("duration"), "descricao": (info.get("description") or "")[:2000] or None}
    (Path(pasta) / "origem.json").write_text(json.dumps(origem, ensure_ascii=False, indent=2), encoding="utf-8")
    return origem


def escolher_legenda(info):
    """Legenda do próprio YouTube no idioma original: manual primeiro, depois a automática "-orig". None se não há."""
    idioma = info.get("language") or ""
    base = idioma.split("-")[0]
    manuais, autos = info.get("subtitles") or {}, info.get("automatic_captions") or {}
    for chave in dict.fromkeys(filter(None, [idioma, base])):
        if chave in manuais:
            return chave, "manual"
    for chave in dict.fromkeys(filter(None, [f"{base}-orig" if base else "", f"{idioma}-orig" if idioma else "", base, idioma])):
        if chave in autos:
            return chave, "auto"
    orig = next((k for k in autos if k.endswith("-orig")), None)
    return (orig, "auto") if orig else None


def _json3(arq):
    segmentos = []
    for ev in json.loads(Path(arq).read_text(encoding="utf-8")).get("events") or []:
        texto = " ".join("".join(s.get("utf8", "") for s in ev.get("segs") or []).split())
        if texto:
            ini = ev.get("tStartMs", 0) / 1000
            segmentos.append({"inicio": ini, "fim": ini + ev.get("dDurationMs", 0) / 1000, "texto": texto})
    return segmentos


def _gravar(ref, idioma, segmentos, fonte, texto=None):
    texto = texto if texto is not None else " ".join(s["texto"] for s in segmentos)
    r = {"idioma": idioma, "fonte": fonte, "segmentos": segmentos}
    (ref / "transcricao.txt").write_text(" ".join(texto.split()), encoding="utf-8")
    (ref / "transcricao.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    return r


def _http_get(url, timeout=None):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout or 60) as r:
        return r.read()


def legenda_youtube(pasta, url, timeout=None, executar=None, http_get=None):
    """Legenda do YouTube, sem baixar vídeo nem transcrever: primeiro pela URL que já veio no video.info.json do download
    (nenhuma chamada nova ao YouTube, que pede login quando vê muitas seguidas); URL expirada, pelo yt-dlp.
    None se o vídeo não tem legenda ou as duas vias falharam."""
    ref = Path(pasta) / "referencia"
    try:
        info = json.loads((ref / "video.info.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    escolha = escolher_legenda(info)
    if not escolha:
        return None
    chave, tipo = escolha
    arq = ref / f"legenda.{chave}.json3"
    formatos = ((info.get("subtitles") if tipo == "manual" else info.get("automatic_captions")) or {}).get(chave) or []
    direta = next((f.get("url") for f in formatos if f.get("ext") == "json3" and f.get("url")), None)
    if direta:
        try:
            arq.write_bytes((http_get or _http_get)(direta, timeout=60))
            segmentos = _json3(arq)
            if segmentos:
                return _gravar(ref, chave.split("-")[0], segmentos, f"youtube:{chave}")
        except (OSError, ValueError):
            arq.unlink(missing_ok=True)
    cmd = ["yt-dlp", "--skip-download", "--write-subs" if tipo == "manual" else "--write-auto-subs", "--sub-langs", chave,
           "--sub-format", "json3", "-o", str(ref / "legenda"), url]
    codigo, _ = _rodar(executar)(cmd, timeout=timeout)
    if codigo != 0 or not arq.exists():
        return None
    segmentos = _json3(arq)
    if not segmentos:
        return None
    return _gravar(ref, chave.split("-")[0], segmentos, f"youtube:{chave}")


def transcrever(pasta, timeout=None, executar=None, modelo=None, url=None, http_get=None):
    """Legenda do YouTube quando existe (pedido do Usuário, 28/09/2026); senão, whisper local."""
    ref = Path(pasta) / "referencia"
    if url:
        r = legenda_youtube(pasta, url, timeout=timeout, executar=executar, http_get=http_get)
        if r:
            return r
    modelo = modelo or os.environ.get("RECRIAR_WHISPER_MODELO", "small")
    cmd = ["whisper", str(ref / "video.mp4"), "--model", modelo, "--task", "transcribe", "--output_format", "json",
           "--output_dir", str(ref), "--fp16", "False", "--verbose", "False"]
    codigo, saida = _rodar(executar)(cmd, timeout=timeout)
    bruto = ref / "video.json"
    if codigo != 0 or not bruto.exists():
        raise Erro(f"whisper não transcreveu a referência (código {codigo}): {saida.strip()[-300:]}")
    dados = json.loads(bruto.read_text(encoding="utf-8"))
    segmentos = [{"inicio": s["start"], "fim": s["end"], "texto": s["text"].strip()} for s in dados.get("segments") or []]
    return _gravar(ref, dados.get("language"), segmentos, "whisper", texto=dados.get("text") or "")


def quantidade_quadros(duracao):
    return max(1, math.ceil(duracao / INTERVALO_QUADROS))


def _duracao(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video)],
                       capture_output=True, text=True, check=True, timeout=60)
    return float(json.loads(r.stdout)["format"]["duration"])


def quadros(pasta):
    ref = Path(pasta) / "referencia"
    video = ref / "video.mp4"
    destino = ref / "quadros"
    destino.mkdir(parents=True, exist_ok=True)
    saida = []
    for i in range(quantidade_quadros(_duracao(video))):
        t = i * INTERVALO_QUADROS
        arq = destino / f"{t:03d}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(video), "-frames:v", "1", "-vf", "scale=-2:540",
                        "-q:v", "4", str(arq)], check=True, capture_output=True, timeout=120)
        if arq.exists():
            saida.append(arq)
    return saida
