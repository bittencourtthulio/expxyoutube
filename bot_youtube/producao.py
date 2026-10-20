"""Produção de um pedido: referência (baixar, transcrever, quadros), a skill /recriar-aula-youtube num claude sem
cabeça dentro do cursos-ia, e o resultado (recriacao.json ou falha.txt) vira aguardando_envio, com slot reservado
e prévia, ou falhou com o motivo. Um pedido por vez (estado/bot-youtube/producao.lock).

O claude roda sem nenhuma variável TELEGRAM_* e sem poder ler arquivo de chaves, tokens ou publicar (D-05, D-21).
"""
import fcntl
import json
import os
import shutil
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from comum import SP

from . import canal as _canal
from . import executar as _executar
from . import pedidos, previa, referencia, slots, sonda_heygen

PROIBIDO = " ".join([
    "Read(./.env)", "Read(../youtube-squad/.env)", "Read(../youtube-squad/tokens/**)", "Read(../youtube-squad/client_secret*)",
    "Bash(cat .env:*)", "Bash(cat ../youtube-squad/.env:*)",
    "Bash(python3 ../youtube-squad/publicacao.py:*)", "Bash(python ../youtube-squad/publicacao.py:*)", "Bash(git push:*)",
])
FILA = {"na_fila", "ajuste"}
PRAZO_ANTES = timedelta(minutes=60)


def ambiente_claude():
    """Ambiente do claude da produção: o do bot sem nenhuma variável TELEGRAM_*."""
    return {k: v for k, v in os.environ.items() if not k.startswith("TELEGRAM")}


def _rodar_padrao(cmd, timeout=None, cwd=None, env=None):
    return _executar.rodar(cmd, timeout=timeout, cwd=cwd, env=env)


def _disco_livre(caminho):
    return shutil.disk_usage(caminho).free


def comando(pasta, pid, modo, ajuste=None):
    pedido = f"/recriar-aula-youtube {pasta} {pid} {modo}" + (f" ajuste: {ajuste}" if ajuste else "")
    return ["claude", "-p", pedido, "--permission-mode", "bypassPermissions", "--disallowedTools", PROIBIDO]


ROTULO_ETAPA = {"preflight": "conferência do ambiente concluída", "roteiro": "roteiro concluído", "saldo": "saldo do HeyGen conferido",
                "voz": "voz concluída", "avatar": "avatar concluído", "legendas": "legendas concluídas", "visual": "revisão visual concluída",
                "render": "render concluído", "pacote": "pacote concluído"}


def aula_do_pedido(pid, cursos_ia):
    """A aula que a skill criou para o pedido: a de qualquer série cujo DESFAZER.md cita o id."""
    base = Path(cursos_ia) / "series"
    for desfazer in sorted(base.glob("*/*/DESFAZER.md"), key=lambda p: p.stat().st_mtime, reverse=True) if base.is_dir() else []:
        try:
            if pid in desfazer.read_text(encoding="utf-8"):
                return desfazer.parent
        except OSError:
            continue
    return None


def registrar_progresso(pid, aula):
    """Um evento progresso (avisado no Telegram) por etapa do executor da aula que ficou concluída."""
    try:
        estado = json.loads((Path(aula) / ".producao/estado.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    ja = {e.get("etapa_aula") for e in pedidos.eventos(pid) if e["etapa"] == "progresso"}
    novos = []
    for etapa, info in estado.items():
        if (info or {}).get("status") == "concluido" and etapa in ROTULO_ETAPA and etapa not in ja:
            from .mensagens import PCT_ETAPA
            pedidos.registrar_evento(pid, "progresso", avisar=True, etapa_aula=etapa, nota=ROTULO_ETAPA[etapa], pct=PCT_ETAPA.get(etapa))
            novos.append(etapa)
    return novos


def acompanhar_padrao(pid, parar, cursos_ia, intervalo=60):
    while not parar.wait(intervalo):
        aula = aula_do_pedido(pid, cursos_ia)
        if aula:
            registrar_progresso(pid, aula)


def proximo_trabalho():
    for p in pedidos.pedidos():
        if p["etapa"] in FILA:
            return p["pedido"]
    return None


def _falhou(pid, nota):
    pedidos.registrar_evento(pid, "falhou", avisar=True, nota=nota[:500])
    return "falhou"


def _aviso(pid, nota, marco):
    from .mensagens import PCT_REFERENCIA
    pedidos.registrar_evento(pid, "progresso", avisar=True, nota=nota, pct=PCT_REFERENCIA[marco])


def _referencia(pid, e, restante):
    """Baixa, transcreve (legenda do YouTube; sem ela, whisper) e tira quadros, avisando o Usuário a cada passo."""
    pasta = pedidos.pasta_pedido(pid)
    if not ((pasta / "origem.json").exists() and (pasta / "referencia/video.mp4").exists()):
        _aviso(pid, "baixando o vídeo de referência", "baixando")
        referencia.baixar(e["url"], pasta, timeout=restante())
    try:
        origem = json.loads((pasta / "origem.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        origem = {}
    dur = f" ({round(origem['duracao'] / 60)} min)" if isinstance(origem.get("duracao"), (int, float)) else ""
    _aviso(pid, f"vídeo baixado: {origem.get('titulo') or 'referência'}{dur}", "baixado")
    if not (pasta / "referencia/transcricao.txt").exists():
        _aviso(pid, "buscando a legenda do YouTube (se o vídeo não tiver, transcrevo com o whisper, que demora mais)", "legenda")
        r = referencia.transcrever(pasta, timeout=restante(), url=e.get("url")) or {}
        fonte = str(r.get("fonte") or "")
        _aviso(pid, "transcrição pronta pela legenda do YouTube" if fonte.startswith("youtube") else "transcrição pronta pelo whisper", "transcricao")
    if not (pasta / "referencia/quadros").is_dir():
        referencia.quadros(pasta)
        _aviso(pid, "quadros do vídeo prontos", "quadros")


def _playlists(pasta, cliente):
    try:
        lista = _canal.playlists(cliente) if cliente else []
    except Exception:  # noqa: BLE001 - sem lista, a skill cria playlist pelo título
        lista = []
    (pasta / "playlists.json").write_text(json.dumps(lista, ensure_ascii=False), encoding="utf-8")


def _modo(pid, e):
    modo = e.get("modo") or "motion"
    if modo == "avatar":
        sonda = sonda_heygen.ultima() or {}
        if not sonda.get("ok"):
            pedidos.registrar_evento(pid, "progresso", avisar=True, modo_efetivo="motion", pct=19,
                                     nota=f"HeyGen indisponível sem supervisão ({sonda.get('motivo') or 'sonda não rodou'}): vou produzir só motion")
            return "motion"
    return modo


def _horario(pid, e, cfg, cliente, agora):
    agendados = _canal.agendados(cliente) if cliente else []
    antigo = e.get("horario")
    if antigo:   # ajuste/refazer: mantém o horário se ainda está livre e a tempo
        dt = datetime.fromisoformat(antigo)
        if dt - agora >= timedelta(minutes=cfg.antecedencia_min) and dt.strftime("%H:%M") not in slots.ocupados(dt.date().isoformat(), agendados, ignorar=pid):
            return dt
    return slots.proximo_slot(agora, cfg.slots, agendados, antecedencia_min=cfg.antecedencia_min, ignorar=pid)


def _finalizar(pid, e, cfg, cliente, agora_fn, rec, video, modo):
    """Vídeo pronto: reserva o slot, gera a prévia e deixa o pedido esperando o Usuário (aguardando_envio)."""
    pasta = pedidos.pasta_pedido(pid)
    try:
        horario = _horario(pid, e, cfg, cliente, agora_fn())
        arq_previa = previa.gerar(video, pasta / "previa.mp4")
    except Exception as erro:  # noqa: BLE001
        return _falhou(pid, f"depois do vídeo pronto: {erro}")
    envio = max(horario - PRAZO_ANTES, agora_fn())
    pedidos.registrar_evento(pid, "aguardando_envio", avisar=True, horario=horario.isoformat(timespec="seconds"),
                             envio_em=envio.isoformat(timespec="seconds"), previa=str(arq_previa), thumb=rec.get("thumb"),
                             titulo=rec.get("titulo"), video=str(video), aula=rec.get("aula"), modo_efetivo=rec.get("modo") or modo)
    return "aguardando_envio"


def retomar(pid, cfg, cliente=None, agora=None):
    """Produção que terminou fora do bot (bot parado ou reiniciado no meio): se o recriacao.json do pedido está
    pronto, leva direto à prévia, sem produzir de novo. Pedido já pronto ou enviado fica como está."""
    agora_fn = agora or (lambda: datetime.now(SP))
    e = pedidos.estado_pedido(pid) or {}
    if e.get("etapa") not in ("produzindo", "falhou", "na_fila"):
        return e.get("etapa")
    rec_arq = pedidos.pasta_pedido(pid) / "recriacao.json"
    if not rec_arq.exists():
        return "sem_recriacao"
    rec = json.loads(rec_arq.read_text(encoding="utf-8"))
    video = Path(rec.get("video") or "")
    if rec.get("pedido") != pid or not video.exists():
        return "sem_recriacao"
    return _finalizar(pid, e, cfg, cliente, agora_fn, rec, video, rec.get("modo") or e.get("modo") or "motion")


def produzir(pid, cfg, executar=None, cliente=None, agora=None, disco_livre=None, acompanhar=None):
    agora_fn = agora or (lambda: datetime.now(SP))
    rodar = executar or _rodar_padrao
    trava_arq = pedidos.ESTADO / "producao.lock"
    trava_arq.parent.mkdir(parents=True, exist_ok=True)
    with open(trava_arq, "w") as trava:
        try:
            fcntl.flock(trava, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return "ocupado"
        e = pedidos.estado_pedido(pid) or {}
        if e.get("etapa") not in FILA:
            return e.get("etapa")
        ajuste = e.get("ajuste_pendente") if e["etapa"] == "ajuste" else None
        pedidos.registrar_evento(pid, "produzindo", avisar=True, modo=e.get("modo"))
        livre = (disco_livre or _disco_livre)(cfg.cursos_ia)
        if livre < cfg.disco_min_gb * 1024 ** 3:
            return _falhou(pid, f"disco: {livre / 1024 ** 3:.1f} GB livres, mínimo {cfg.disco_min_gb} GB (YT_DISCO_MIN_GB)")
        prazo = time.monotonic() + cfg.tempo_producao_min * 60

        def restante():
            return max(int(prazo - time.monotonic()), 60)

        pasta = pedidos.pasta_pedido(pid)
        try:
            _referencia(pid, e, restante)
        except Exception as erro:  # noqa: BLE001
            return _falhou(pid, f"referência: {erro}")
        _playlists(pasta, cliente)
        modo = _modo(pid, e)
        _aviso(pid, "começando a aula: roteiro, voz, cenas e render (te aviso a cada etapa)", "aula")
        (pasta / "falha.txt").unlink(missing_ok=True)
        inicio = time.time()
        parar = threading.Event()
        vigia = acompanhar or (lambda p, ev: acompanhar_padrao(p, ev, cfg.cursos_ia))
        threading.Thread(target=vigia, args=(pid, parar), daemon=True).start()
        try:
            codigo, saida = rodar(comando(pasta, pid, modo, ajuste), timeout=restante(), cwd=str(cfg.cursos_ia), env=ambiente_claude())
        finally:
            parar.set()
        if (pedidos.estado_pedido(pid) or {}).get("etapa") == "cancelado":
            return "cancelado"
        rec_arq, falha = pasta / "recriacao.json", pasta / "falha.txt"
        if falha.exists():
            return _falhou(pid, f"a produção parou: {falha.read_text(encoding='utf-8').strip()}")
        if not rec_arq.exists() or rec_arq.stat().st_mtime < inicio:
            return _falhou(pid, f"o claude terminou sem recriacao.json (código {codigo}): {saida.strip()[-300:]}")
        rec = json.loads(rec_arq.read_text(encoding="utf-8"))
        video = Path(rec.get("video") or "")
        if rec.get("pedido") != pid or not video.exists():
            return _falhou(pid, "recriacao.json de outro pedido ou sem o vídeo")
        if ajuste and video.stat().st_mtime < inicio:
            return _falhou(pid, "video nao foi refeito depois do ajuste; a versão de antes ficou parada")
        return _finalizar(pid, e, cfg, cliente, agora_fn, rec, video, modo)
