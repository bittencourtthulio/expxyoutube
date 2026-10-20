"""Pedidos do bot: cada um é uma sequência de eventos em estado/bot-youtube/pedidos.jsonl (só acréscimo, com flock)
e uma pasta estado/bot-youtube/pedidos/<pedido>/ com a referência baixada."""
import fcntl
import json
import os
from datetime import datetime
from pathlib import Path

from comum import SP

# BOT_YT_ESTADO troca a pasta (testes da CLI em subprocesso); o bot de verdade usa estado/bot-youtube do squad
ESTADO = Path(os.environ.get("BOT_YT_ESTADO") or Path(__file__).resolve().parent.parent / "estado" / "bot-youtube")
# eventos que só registram algo (aviso de progresso, id da prévia) e não mudam a etapa do pedido
INFORMATIVOS = {"progresso", "previa_enviada"}


def agora():
    return datetime.now(SP)


def arquivo():
    return ESTADO / "pedidos.jsonl"   # resolvido na hora: os testes trocam o ESTADO


def pasta_pedido(pid):
    return ESTADO / "pedidos" / pid


def eventos(pid=None):
    caminho = arquivo()
    if not caminho.exists():
        return []
    evs = [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [e for e in evs if pid is None or e.get("pedido") == pid]


def _acrescentar(evento):
    caminho = arquivo()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")
        f.flush()
    return evento


def registrar_evento(pid, etapa, avisar=False, quando=None, **dados):
    evento = {"quando": (quando or agora()).isoformat(timespec="seconds"), "pedido": pid, "etapa": etapa, "avisar": bool(avisar)}
    evento.update({k: v for k, v in dados.items() if v is not None})
    return _acrescentar(evento)


def novo_pedido(url=None, texto="", origem="telegram", quando=None, etapa="recebido", **dados):
    quando = quando or agora()
    existentes = {e["pedido"] for e in eventos()}
    base = "y" + quando.strftime("%Y%m%d-%H%M%S")
    pid, n = base, 1
    while pid in existentes:
        n += 1
        pid = f"{base}-{n}"
    pasta_pedido(pid).mkdir(parents=True, exist_ok=True)
    registrar_evento(pid, etapa, quando=quando, url=url, texto=texto or None, origem=origem, **dados)
    return pid


def estado_pedido(pid):
    evs = eventos(pid)
    if not evs:
        return None
    estado = {}
    for e in evs:
        estado.update({k: v for k, v in e.items() if k != "avisar" and not (k == "etapa" and e["etapa"] in INFORMATIVOS)})
    estado["criado_em"] = evs[0]["quando"]
    estado["historico"] = [{"quando": e["quando"], "etapa": e["etapa"], **({"nota": e["nota"]} if e.get("nota") else {})} for e in evs]
    ultimo_ajuste = max((i for i, e in enumerate(evs) if e["etapa"] == "ajuste"), default=-1)
    ultima_peca = max((i for i, e in enumerate(evs) if e["etapa"] == "aguardando_envio"), default=-1)
    estado["ajuste_pendente"] = evs[ultimo_ajuste].get("ajuste") if ultimo_ajuste > ultima_peca else None
    return estado


def pedidos():
    ordem = []
    for e in eventos():
        if e["pedido"] not in ordem:
            ordem.append(e["pedido"])
    return [estado_pedido(p) for p in ordem]
