"""Transições do pedido. Cada função devolve (ok, texto para o Usuário) e só grava evento quando a transição vale.

Etapas: aguardando_escolha → na_fila → produzindo → aguardando_envio (horário reservado, envio_em = horário − 60 min)
→ aprovado → enviando → enviado. Laterais: aguardando_ajuste → ajuste (volta à produção), reagendado, cancelado,
falhou (Refazer volta a na_fila), bloqueado."""
from datetime import datetime

from comum import SP

from . import pedidos

MODOS = {"motion": "só motion", "avatar": "com avatar"}
TERMINAIS = {"enviado", "cancelado"}
PRONTOS = {"aguardando_envio", "reagendado"}


def _quando(iso):
    return datetime.fromisoformat(iso).strftime("%d/%m às %H:%M")


def _agora():
    return datetime.now(SP)


def escolher_modo(pid, modo):
    e = pedidos.estado_pedido(pid)
    if not e:
        return False, f"O pedido {pid} não existe."
    if modo not in MODOS:
        return False, f"Modo desconhecido: {modo}."
    if e["etapa"] != "aguardando_escolha":
        return False, f"{pid} está {e['etapa']}; a escolha do modo é só antes da produção."
    pedidos.registrar_evento(pid, "na_fila", modo=modo, nota=f"escolha do Usuário: {MODOS[modo]}")
    return True, f"{pid}: vou produzir a aula {MODOS[modo]}. Te aviso a cada etapa."


def cancelar(pid, cliente_fn=None):
    """Antes do upload, cancela de verdade. Depois, tira o agendamento: o vídeo fica privado no canal e o slot fica livre (D-18)."""
    e = pedidos.estado_pedido(pid)
    if not e:
        return False, f"O pedido {pid} não existe."
    if e["etapa"] == "enviado":
        if not cliente_fn or not e.get("video_id"):
            return False, f"{pid} já está no YouTube (vídeo {e.get('video_id')}); sem acesso ao canal agora para tirar o agendamento."
        from . import canal
        canal.desagendar(cliente_fn(), e["video_id"])
        pedidos.registrar_evento(pid, "cancelado", nota=f"vídeo {e['video_id']} privado, sem agendamento")
        return True, f"{pid} cancelado. O vídeo {e['video_id']} ficou privado no canal, sem agendamento, e o horário ficou livre."
    if e["etapa"] in TERMINAIS:
        return False, f"{pid} já está {e['etapa']}."
    if e["etapa"] == "enviando":
        return False, f"{pid} está subindo para o YouTube agora. Espere o aviso e cancele de novo."
    pedidos.registrar_evento(pid, "cancelado", nota="cancelado pelo Usuário")
    return True, f"{pid} cancelado. Não vai para o YouTube."


def refazer(pid):
    e = pedidos.estado_pedido(pid)
    if not e:
        return False, f"O pedido {pid} não existe."
    if e["etapa"] != "falhou":
        return False, f"{pid} está {e['etapa']}; o Refazer só vale para pedido que falhou."
    pedidos.registrar_evento(pid, "na_fila", nota="refazer pedido pelo Usuário")
    return True, f"{pid} voltou para a fila de produção."


def aprovar(pid, agora=None):
    e = pedidos.estado_pedido(pid)
    if not e:
        return False, f"O pedido {pid} não existe."
    if e["etapa"] == "aprovado":
        return False, f"{pid} já foi aprovado; está subindo para o YouTube."
    if e["etapa"] not in PRONTOS:
        return False, f"{pid} está {e['etapa']}: só vídeo pronto, esperando envio, pode ser aprovado."
    agora = (agora or _agora()).isoformat(timespec="seconds")
    pedidos.registrar_evento(pid, "aprovado", envio_em=agora, aprovado_em=agora)
    return True, f"{pid} aprovado. Sobe agora para o YouTube, agendado para {_quando(e['horario'])}."


def pedir_ajuste(pid):
    e = pedidos.estado_pedido(pid)
    if not e:
        return False, f"O pedido {pid} não existe."
    if e["etapa"] == "aguardando_ajuste":
        return True, f"{pid} já está esperando o ajuste. Escreva ou mande um áudio dizendo o que mudar."
    if e["etapa"] not in PRONTOS:
        return False, f"{pid} está {e['etapa']}: só vídeo pronto, ainda não aprovado, pode ser ajustado."
    pedidos.registrar_evento(pid, "aguardando_ajuste", ajuste_pedido_em=_agora().isoformat(timespec="seconds"),
                             nota="Usuário pediu ajuste; o vídeo não sobe até ele dizer qual")
    return True, f"Qual é o ajuste do {pid}? Escreva ou mande um áudio. O vídeo fica seguro até lá e o horário continua reservado."


def ajustar(pid, texto, origem="texto"):
    texto = (texto or "").strip()
    e = pedidos.estado_pedido(pid)
    if not e:
        return False, f"O pedido {pid} não existe."
    if not texto:
        return False, "O ajuste veio vazio. Escreva ou mande um áudio de novo."
    if e["etapa"] not in PRONTOS | {"aguardando_ajuste"}:
        return False, f"{pid} está {e['etapa']}: só vídeo pronto, ainda não aprovado, pode ser ajustado."
    pedidos.registrar_evento(pid, "ajuste", ajuste=texto, ajuste_origem=origem, nota=f"ajuste do Usuário: {texto[:300]}")
    return True, f"Entendi o ajuste do {pid}:\n“{texto}”\nEntrou na fila. A nova prévia chega aqui."


def manter(pid):
    e = pedidos.estado_pedido(pid)
    if not e:
        return False, f"O pedido {pid} não existe."
    if e["etapa"] != "aguardando_ajuste":
        return False, f"{pid} está {e['etapa']}: não está esperando ajuste."
    pedidos.registrar_evento(pid, "reagendado", nota="Usuário desistiu do ajuste: segue o vídeo como estava")
    return True, f"{pid} segue como estava, agendado para {_quando(e['horario'])}."


def aguardando_ajuste():
    ps = [p for p in pedidos.pedidos() if p["etapa"] == "aguardando_ajuste"]
    return max(ps, key=lambda p: p.get("ajuste_pedido_em") or "")["pedido"] if ps else None


def vencidos(agora=None):
    """Pedidos que sobem agora: aprovados, e os prontos cujo prazo (envio_em = horário − 60 min) chegou."""
    agora = agora or _agora()
    saida = []
    for p in pedidos.pedidos():
        if p["etapa"] == "aprovado" or (p["etapa"] in PRONTOS and p.get("envio_em") and datetime.fromisoformat(p["envio_em"]) <= agora):
            saida.append(p)
    return saida
