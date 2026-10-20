"""Enviador: a cada 30 s (ou já, quando o Usuário aprova) sobe os pedidos vencidos — aprovados e os prontos cujo prazo
(1 h antes do slot) chegou. Slot a menos de 15 min que ainda não subiu ganha slot novo. Login expirado vira
`bloqueado` com o comando de relogin, sem repetir (D-31). Uma instância por vez (estado/bot-youtube/envio.lock)."""
import fcntl
import logging
from datetime import datetime, timedelta

from comum import SP

from . import canal as _canal
from . import pedidos, publicar, slots

log = logging.getLogger("bot_youtube")
MARGEM = timedelta(minutes=15)
PRAZO_ANTES = timedelta(minutes=60)


def _bloquear_auth(p, erro, cfg):
    pedidos.registrar_evento(p["pedido"], "bloqueado", avisar=True,
                             nota=f"o login do canal {cfg.canal_alias} expirou ({str(erro)[:120]}): rode no youtube-squad "
                                  f"`.venv/bin/python auth.py {cfg.canal_alias}` e depois Refazer")


def girar(cfg, agora=None, enviar=None, cliente_fn=None):
    import yt
    agora = agora or datetime.now(SP)
    enviar = enviar or (lambda pid, c, motivo=None: publicar.enviar(pid, c, motivo=motivo))
    cliente_fn = cliente_fn or (lambda: _canal.conectar(cfg.canal_alias))
    trava_arq = pedidos.ESTADO / "envio.lock"
    trava_arq.parent.mkdir(parents=True, exist_ok=True)
    feitos = []
    from . import fluxo
    with open(trava_arq, "w") as trava:
        try:
            fcntl.flock(trava, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return []
        for p in fluxo.vencidos(agora):
            pid = p["pedido"]
            horario = datetime.fromisoformat(p["horario"])
            if horario - agora < MARGEM:
                try:
                    novo = slots.proximo_slot(agora, cfg.slots, _canal.agendados(cliente_fn()), antecedencia_min=cfg.antecedencia_min, ignorar=pid)
                except yt.ErroAuth as erro:
                    _bloquear_auth(p, erro, cfg)
                    continue
                except slots.Erro as erro:
                    pedidos.registrar_evento(pid, "falhou", avisar=True, nota=str(erro))
                    continue
                envio = agora if p.get("aprovado_em") else max(novo - PRAZO_ANTES, agora)
                pedidos.registrar_evento(pid, "reagendado", avisar=True, horario=novo.isoformat(timespec="seconds"),
                                         envio_em=envio.isoformat(timespec="seconds"),
                                         nota=f"o vídeo não subiu a tempo das {horario.strftime('%H:%M')}")
                continue
            motivo = f"aprovado no Telegram em {p['aprovado_em']}" if p.get("aprovado_em") else "prazo de 1 h antes do slot sem resposta do Usuário"
            try:
                if enviar(pid, cfg, motivo=motivo) == "enviado":
                    feitos.append(pid)
            except yt.ErroAuth as erro:
                _bloquear_auth(p, erro, cfg)
            except Exception as erro:  # noqa: BLE001 - um pedido ruim não trava os outros
                log.exception("envio de %s", pid)
                pedidos.registrar_evento(pid, "falhou", avisar=True, nota=f"erro ao subir: {str(erro)[:300]}")
    return feitos


def laco(parar, acordar, cfg):
    while not parar.is_set():
        acordar.wait(30)
        acordar.clear()
        if parar.is_set():
            return
        try:
            girar(cfg)
        except Exception:  # noqa: BLE001
            log.exception("enviador")
