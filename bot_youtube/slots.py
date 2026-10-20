"""Horários do bot: os slots fixos de YT_SLOTS (todo dia, America/Sao_Paulo), menos os já tomados no canal
(publishAt) e pelos pedidos do bot que reservaram horário (D-08, D-09, D-25)."""
from datetime import datetime, timedelta

from comum import SP

from . import pedidos

ATIVOS = {"aguardando_envio", "reagendado", "aprovado", "enviando", "enviado", "aguardando_ajuste", "ajuste"}


class Erro(Exception):
    pass


def ocupados(data, agendados, ignorar=None):
    """Horas (HH:MM) tomadas no dia `data` (AAAA-MM-DD): publishAt do canal e pedidos ativos com horário."""
    horas = {h.astimezone(SP).strftime("%H:%M") for h in agendados if h.astimezone(SP).date().isoformat() == data}
    for p in pedidos.pedidos():
        if p["pedido"] != ignorar and p["etapa"] in ATIVOS and str(p.get("horario", ""))[:10] == data:
            horas.add(p["horario"][11:16])
    return sorted(horas)


def proximo_slot(agora, horarios, agendados, antecedencia_min=90, dias=60, ignorar=None):
    """Primeiro slot livre a `antecedencia_min` ou mais de agora, procurando até `dias` dias."""
    agora = agora.astimezone(SP)
    piso = agora + timedelta(minutes=antecedencia_min)
    for n in range(dias + 1):
        dia = (agora + timedelta(days=n)).date()
        tomadas = set(ocupados(dia.isoformat(), agendados, ignorar=ignorar))
        for h in sorted(horarios):
            hh, mm = map(int, h.split(":"))
            candidato = datetime(dia.year, dia.month, dia.day, hh, mm, tzinfo=SP)
            if candidato >= piso and h not in tomadas:
                return candidato
    raise Erro(f"nenhum slot livre nos proximos {dias} dias")
