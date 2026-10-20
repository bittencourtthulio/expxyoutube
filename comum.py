"""Utilitários compartilhados: arquivo, jsonl, número válido e fusos.

Todo módulo do harness lê e grava estado por aqui, para que a regra seja uma só:
gravação atômica, jsonl só por acréscimo com trava, e linha corrompida pulada e contada
(nunca derruba a leitura inteira).
"""
import fcntl
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SP = ZoneInfo("America/Sao_Paulo")
PACIFICO = ZoneInfo("America/Los_Angeles")  # o "dia" da YouTube Analytics API
UTC = timezone.utc


def ler_json(caminho, padrao=None):
    """JSON do arquivo, ou `padrao` se ele não existe ou não é JSON válido."""
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return padrao


def gravar_json(caminho, dados):
    """Grava por arquivo temporário + os.replace: quem lê nunca vê meio arquivo."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=caminho.parent, prefix=caminho.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, caminho)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def anexar_jsonl(caminho, evento):
    """Acrescenta um evento numa linha, com trava exclusiva."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    linha = json.dumps(evento, ensure_ascii=False) + "\n"
    with open(caminho, "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(linha)
            f.flush()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def ler_jsonl(caminho):
    """(eventos, corrompidas). Linha em branco é ignorada; linha inválida é pulada e contada."""
    try:
        texto = Path(caminho).read_text(encoding="utf-8")
    except OSError:
        return [], 0
    eventos, corrompidas = [], 0
    for linha in texto.splitlines():
        if not linha.strip():
            continue
        try:
            evento = json.loads(linha)
        except ValueError:
            corrompidas += 1
            continue
        if isinstance(evento, dict):
            eventos.append(evento)
        else:
            corrompidas += 1
    return eventos, corrompidas


def numero(v, sinal=False):
    """Número de verdade: int/float finito, não bool; negativo só com `sinal=True`."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return False
    return sinal or v >= 0


def valor(v, sinal=False):
    """O próprio valor se for número válido, senão None. Ausência nunca vira zero."""
    return v if numero(v, sinal) else None


def agora():
    return datetime.now(SP)


def agora_iso():
    return agora().isoformat(timespec="seconds")


def hoje_sp(instante=None):
    return (instante or datetime.now(UTC)).astimezone(SP).date().isoformat()


def hoje_pacifico(instante=None):
    return (instante or datetime.now(UTC)).astimezone(PACIFICO).date().isoformat()
