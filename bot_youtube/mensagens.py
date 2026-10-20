"""Textos e teclados do bot do YouTube."""
import json
from datetime import datetime

AJUDA = ("Me manda o link de um vídeo do YouTube. Eu pergunto se a aula sai com avatar ou só motion, produzo a aula "
         "no nosso padrão e te mando a prévia com Aprovar (sobe agora, no próximo horário livre), Ajustar (você diz, por "
         "texto ou áudio, o que mudar) e Cancelar. Sem resposta, o vídeo sobe sozinho 1 h antes do horário.\n\n"
         "/fila  pedidos e etapa de cada um\n/status <pedido>  detalhe de um pedido\n/ajuda  esta mensagem")

PERGUNTA_MODO = "Como você quer a aula?\nCom avatar: você em PiP no canto, sobre o motion.\nSó motion: animação em tela cheia."

ROTULO = {"aguardando_escolha": "esperando você escolher o modo", "na_fila": "na fila de produção", "produzindo": "produzindo",
          "aguardando_envio": "pronto, esperando envio", "reagendado": "pronto, esperando envio", "aprovado": "aprovado, subindo",
          "enviando": "subindo para o YouTube", "enviado": "agendado no YouTube", "cancelado": "cancelado", "falhou": "falhou",
          "bloqueado": "bloqueado", "aguardando_ajuste": "esperando você dizer o ajuste", "ajuste": "na fila de ajuste"}


# Percentual de cada marco da produção (pedido do Usuário, 28/09/2026): a barra no topo de cada aviso.
PCT_REFERENCIA = {"baixando": 3, "baixado": 8, "legenda": 10, "transcricao": 15, "quadros": 18, "modo": 19, "aula": 20}
PCT_ETAPA = {"preflight": 22, "roteiro": 30, "saldo": 33, "voz": 45, "avatar": 48, "legendas": 52, "visual": 75,
             "render": 90, "pacote": 95}


def barra(pct, largura=10):
    pct = max(0, min(100, int(pct)))
    cheios = int(pct * largura / 100 + 0.5)
    return "▓" * cheios + "░" * (largura - cheios) + f" {pct}%"


def _teclado(*linhas):
    return json.dumps({"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in linha] for linha in linhas]})


def teclado_modo(pid):
    return _teclado([("Com avatar", f"avatar:{pid}")], [("Só motion", f"motion:{pid}")])


def teclado_previa(pid):
    return _teclado([("Aprovar", f"aprovar:{pid}"), ("Ajustar", f"ajustar:{pid}"), ("Cancelar", f"cancelar:{pid}")])


def teclado_ajuste(pid):
    return _teclado([("Manter como está", f"manter:{pid}"), ("Cancelar", f"cancelar:{pid}")])


def teclado_refazer(pid):
    return _teclado([("Refazer", f"refazer:{pid}")])


def teclado_cancelar(pid):
    return _teclado([("Cancelar", f"cancelar:{pid}")])


SEM_TECLADO = json.dumps({"inline_keyboard": []})


def quando(iso):
    return datetime.fromisoformat(iso).strftime("%d/%m às %H:%M")


def texto_previa(p):
    titulo = f" — {p['titulo']}" if p.get("titulo") else ""
    return (f"{barra(100)}\nPronto: {p['pedido']}{titulo}.\n"
            f"A prévia acima é o primeiro minuto, em 720p; no YouTube sobe o vídeo inteiro em 1080p.\n"
            f"Agendado para {quando(p['horario'])}. Se você não responder, sobe sozinho às {p['envio_em'][11:16]}.\n"
            f"Aprovar sobe agora, no mesmo horário. Ajustar: você me diz o que mudar e eu refaço.")


def linha(p):
    extra = f" · {quando(p['horario'])}" if p.get("horario") and p["etapa"] in ("aguardando_envio", "reagendado", "aprovado", "enviando", "enviado") else ""
    return f"{p['pedido']} · {ROTULO.get(p['etapa'], p['etapa'])}{extra}"


def texto_do_aviso(ev, pedido):
    pid, nota, etapa = ev["pedido"], ev.get("nota"), ev["etapa"]
    if etapa == "produzindo":
        return f"{barra(0)}\n{pid}: produzindo a aula (referência, roteiro, narração, cenas e render; leva de 1 a 4 h)."
    if etapa == "progresso":
        return (f"{barra(ev['pct'])}\n" if isinstance(ev.get("pct"), int) else "") + f"{pid}: {nota}"
    if etapa == "reagendado":
        return f"{pid}: {nota or 'horário mudou'}. Novo horário: {quando(ev['horario'])}." if ev.get("horario") else f"{pid}: {nota}"
    if etapa == "enviado":
        return (f"{pid}: agendado no YouTube para {quando(pedido.get('horario') or ev.get('horario'))} "
                f"(vídeo {ev.get('video_id')}). Ainda dá para Cancelar: ele fica privado, sem agendamento.")
    if etapa == "falhou":
        return f"{pid}: falhou. {nota or ''}\nPara tentar de novo: botão Refazer."
    if etapa == "bloqueado":
        return f"{pid}: bloqueado. {nota or ''}"
    return f"{pid}: {etapa}" + (f" ({nota})" if nota else "")
