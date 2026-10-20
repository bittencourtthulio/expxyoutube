#!/usr/bin/env python3
"""Bot do Telegram do YouTube: o Usuário manda o link de um vídeo, escolhe Com avatar ou Só motion, o cursos-ia
produz a aula recriada, a prévia chega no Telegram (Aprovar, Ajustar, Cancelar) e o vídeo é agendado no principal no
próximo slot de YT_SLOTS. Sem resposta, sobe sozinho 1 h antes do slot.

  python3 bot_youtube.py verificar                       # confere bot, chat, slots e canal; nunca imprime o token
  python3 bot_youtube.py rodar                           # laço do bot (é o que o LaunchAgent roda)
  python3 bot_youtube.py instalar | desinstalar          # LaunchAgent com.canal.telegram-bot-youtube
  python3 bot_youtube.py fila [--json]                   # pedidos e etapa de cada um
  python3 bot_youtube.py ver <pedido>                    # estado completo de um pedido
  python3 bot_youtube.py novo --url <link> --modo motion|avatar   # pedido pela linha de comando (vai direto à fila)
  python3 bot_youtube.py aprovar|cancelar|refazer <pedido>
  python3 bot_youtube.py desagendar <video_id>           # tira o agendamento de um vídeo no canal (fica privado)
  python3 bot_youtube.py retomar <pedido>                # produção terminou fora do bot: leva o resultado à prévia

Token e chat: TELEGRAM_YT_BOT_TOKEN e TELEGRAM_YT_CHATID (ambiente ou arquivo de chaves da raiz). Regras em
.claude/rules/bot-youtube.md; plano em ../cursos-ia/docs/bot-telegram-youtube/.
"""
import argparse
import json
import sys

from bot_youtube import canal, fluxo, pedidos, servico, telegram
from bot_youtube.config import Config, ErroConfig, carregar_config


def _cfg_opcional():
    try:
        return carregar_config()
    except ErroConfig:
        return Config(token="", chat_id=0, slots=[])


def verificar(_a):
    try:
        cfg = carregar_config()
    except ErroConfig as e:
        print(f"config: {e}", file=sys.stderr)
        return 1
    tg = telegram.Telegram(cfg.token, api_base=cfg.api_base)
    try:
        eu = tg.chamar("getMe")
    except telegram.ErroTelegram as e:
        print(f"telegram: {e}", file=sys.stderr)
        return 1
    try:
        cliente = canal.conectar(cfg.canal_alias)
        canal_id = cliente.canal()["id"]
    except Exception as e:  # noqa: BLE001 - ErroAuth/ErroAPI do yt, com a dica de relogin
        print(f"canal {cfg.canal_alias}: {e}", file=sys.stderr)
        return 1
    print(f"bot: @{eu.get('username')} · chat autorizado: {cfg.chat_id} · slots: {', '.join(cfg.slots)}")
    if canal_id != cfg.canal_id:
        print(f"canal {cfg.canal_alias} devolveu {canal_id}, esperado {cfg.canal_id}")
        return 1
    print(f"canal: {cfg.canal_alias} ({canal_id})")
    return 0


def _saida(ok_texto):
    ok, texto = ok_texto
    print(texto)
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    for nome in ("verificar", "rodar", "instalar", "desinstalar"):
        sub.add_parser(nome)
    p = sub.add_parser("fila"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("ver"); p.add_argument("pedido")
    p = sub.add_parser("novo"); p.add_argument("--url", required=True); p.add_argument("--modo", choices=sorted(fluxo.MODOS), required=True)
    for nome in ("aprovar", "cancelar", "refazer"):
        p = sub.add_parser(nome); p.add_argument("pedido")
    p = sub.add_parser("desagendar"); p.add_argument("video_id")
    p = sub.add_parser("retomar"); p.add_argument("pedido")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    if a.cmd in (None, "verificar"):
        return verificar(a)
    if a.cmd == "rodar":
        return servico.rodar()
    if a.cmd == "instalar":
        print(f"LaunchAgent gravado e carregado: {servico.instalar()}\nlog: estado/bot-youtube/bot.log")
        return 0
    if a.cmd == "desinstalar":
        servico.desinstalar()
        print("LaunchAgent removido")
        return 0
    if a.cmd == "fila":
        ps = pedidos.pedidos()
        if a.json:
            print(json.dumps([{k: v for k, v in p.items() if k != "historico"} for p in ps], ensure_ascii=False, indent=2))
        else:
            from bot_youtube import mensagens
            print("\n".join(mensagens.linha(p) for p in ps) or "Nenhum pedido ainda.")
        return 0
    if a.cmd == "ver":
        e = pedidos.estado_pedido(a.pedido)
        if not e:
            print(f"O pedido {a.pedido} não existe.")
            return 1
        print(json.dumps(e, ensure_ascii=False, indent=2))
        return 0
    if a.cmd == "novo":
        pid = pedidos.novo_pedido(url=a.url, etapa="aguardando_escolha", origem="cli")
        ok, texto = fluxo.escolher_modo(pid, a.modo)
        print(f"{texto}\npedido {pid}")
        return 0 if ok else 1
    if a.cmd == "aprovar":
        return _saida(fluxo.aprovar(a.pedido))
    if a.cmd == "refazer":
        return _saida(fluxo.refazer(a.pedido))
    cfg = _cfg_opcional()
    if a.cmd == "cancelar":
        return _saida(fluxo.cancelar(a.pedido, cliente_fn=lambda: canal.conectar(cfg.canal_alias)))
    if a.cmd == "retomar":
        from bot_youtube import producao
        try:
            cliente = canal.conectar(cfg.canal_alias)
        except Exception:  # noqa: BLE001
            cliente = None
        r = producao.retomar(a.pedido, cfg, cliente=cliente)
        print(f"{a.pedido}: {r}")
        return 0 if r == "aguardando_envio" else 1
    if a.cmd == "desagendar":
        corpo = canal.desagendar(canal.conectar(cfg.canal_alias), a.video_id)
        print(f"vídeo {a.video_id} sem agendamento (privado): {json.dumps(corpo['status'], ensure_ascii=False)}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
