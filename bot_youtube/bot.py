"""Conversa no Telegram: classifica updates, trata cliques e o ajuste por texto ou áudio, e avisa cada evento
marcado com avisar (uma vez só). O trabalho pesado (produzir, subir) mora em producao.py e enviador.py."""
import json
import logging
import os
import re
from pathlib import Path

from . import executar, fluxo, mensagens, pedidos

log = logging.getLogger("bot_youtube")

RE_URL = re.compile(r"https?://[^\s<>\"']+")
RE_YOUTUBE = re.compile(r"^https?://(?:www\.|m\.)?(?:youtube\.com/(?:watch\?|shorts/|live/)|youtu\.be/)", re.I)
MODELO_WHISPER = os.environ.get("RECRIAR_WHISPER_MODELO", "small")
VOCABULARIO = "Aula, gancho, roteiro, cena, avatar, motion, legenda, thumbnail, Claude Code, YouTube, IA."


def _autorizado(obj, chat_id):
    de = (obj.get("from") or {}).get("id")
    chat = ((obj.get("message") or obj).get("chat") or {}).get("id")
    return de == chat_id and chat == chat_id


def classificar(update, chat_id):
    if "callback_query" in update:
        cb = update["callback_query"]
        if not _autorizado(cb, chat_id):
            return {"tipo": "ignorado", "motivo": "callback de outro usuário"}
        return {"tipo": "callback", "id": cb["id"], "data": cb.get("data") or "", "message_id": (cb.get("message") or {}).get("message_id")}
    msg = update.get("message")
    if not msg:
        return {"tipo": "ignorado", "motivo": "tipo de update não tratado"}
    if not _autorizado(msg, chat_id):
        return {"tipo": "ignorado", "motivo": f"chat {(msg.get('chat') or {}).get('id')} não autorizado"}
    base = {"message_id": msg.get("message_id")}
    doc = msg.get("document") or {}
    audio = msg.get("voice") or msg.get("audio") or (doc if str(doc.get("mime_type", "")).startswith("audio/") else None)
    if audio:
        return {**base, "tipo": "audio", "file_id": audio["file_id"]}
    texto = msg.get("text") or ""
    if texto.startswith("/"):
        return {**base, "tipo": "comando", "texto": texto}
    url = next((e["url"] for e in msg.get("entities") or [] if e.get("type") == "text_link"), None)
    if not url:
        m = RE_URL.search(texto)
        url = m.group(0).rstrip(".,;)") if m else None
    if url and RE_YOUTUBE.search(url):
        return {**base, "tipo": "link_youtube", "url": url, "texto": texto}
    return {**base, "tipo": "texto", "texto": texto}


def transcrever(audio, env=None):
    """Texto do áudio do ajuste, pelo whisper local (nada sai da máquina)."""
    audio = Path(audio)
    cmd = ["whisper", str(audio), "--model", MODELO_WHISPER, "--language", "pt", "--task", "transcribe", "--output_format", "txt",
           "--output_dir", str(audio.parent), "--fp16", "False", "--verbose", "False", "--initial_prompt", VOCABULARIO]
    codigo, saida = executar.rodar(cmd, timeout=600, env=env)
    if codigo != 0:
        raise RuntimeError(f"whisper saiu {codigo}: {saida[-200:]}")
    txt = audio.with_suffix(".txt")
    return " ".join(txt.read_text(encoding="utf-8").split()) if txt.exists() else ""


def responder_comando(texto):
    nome, _, args = texto.lstrip("/").partition(" ")
    nome, args = nome.split("@")[0].lower(), args.strip()
    if nome == "fila":
        ps = pedidos.pedidos()[-15:]
        return "Nenhum pedido ainda." if not ps else "Pedidos (mais recentes no fim):\n" + "\n".join(mensagens.linha(p) for p in ps)
    if nome == "status":
        p = pedidos.estado_pedido(args) if args else None
        if not p:
            return "Use /status <pedido>. Os ids aparecem em /fila."
        return "\n".join([mensagens.linha(p)] + [f"  {h['quando'][11:16]} {h['etapa']}" + (f": {h['nota']}" if h.get("nota") else "")
                                                  for h in p["historico"][-8:]])
    return mensagens.AJUDA


class Bot:
    def __init__(self, tg, chat_id, despachar=None, acordar_envio=None, transcrever_env=None, cliente_fn=None):
        self.tg, self.chat_id = tg, chat_id
        self.cliente_fn = cliente_fn
        self.despachar = despachar or (lambda: None)
        self.acordar_envio = acordar_envio or (lambda: None)
        self.transcrever_env = transcrever_env
        self.arquivo = pedidos.ESTADO / "telegram.json"
        self.estado = self._carregar()

    def _carregar(self):
        if self.arquivo.exists():
            return json.loads(self.arquivo.read_text(encoding="utf-8"))
        # primeira subida: o passado não vira enxurrada de mensagens
        return {"offset": 0, "avisados": [self._chave(e) for e in pedidos.eventos() if e.get("avisar")]}

    def _salvar(self):
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        self.estado["avisados"] = self.estado["avisados"][-2000:]
        tmp = self.arquivo.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.estado, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.arquivo)

    @staticmethod
    def _chave(ev):
        return f"{ev['pedido']}|{ev['quando']}|{ev['etapa']}"

    def dizer(self, texto, **extra):
        return self.tg.chamar("sendMessage", {"chat_id": self.chat_id, "text": texto[:4000], **extra})

    def _responder_clique(self, c, texto, teclado=None):
        self.tg.chamar("answerCallbackQuery", {"callback_query_id": c["id"], "text": texto[:190]})
        if teclado is not None and c.get("message_id"):
            self.tg.chamar("editMessageReplyMarkup", {"chat_id": self.chat_id, "message_id": c["message_id"], "reply_markup": teclado})

    def passo(self, timeout=25):
        ups = self.tg.chamar("getUpdates", {"offset": self.estado["offset"], "timeout": timeout,
                                            "allowed_updates": json.dumps(["message", "callback_query"])}, timeout=timeout + 15)
        for u in ups or []:
            try:
                self.tratar(u)
            except Exception as e:  # noqa: BLE001 - um update ruim não trava a fila
                log.exception("update %s: %s", u.get("update_id"), e)
            self.estado["offset"] = u["update_id"] + 1
            self._salvar()
        self.avisar()
        self._salvar()

    def tratar(self, u):
        c = classificar(u, self.chat_id)
        tipo = c["tipo"]
        esperando = fluxo.aguardando_ajuste() if tipo in ("texto", "audio") else None
        if tipo == "ignorado":
            log.info("ignorado: %s", c.get("motivo"))
        elif tipo == "texto" and esperando:
            self.receber_ajuste(esperando, c["texto"], "texto")
        elif tipo == "audio":
            if not esperando:
                self.dizer("Recebi um áudio, mas nenhum vídeo está esperando ajuste. Aperte Ajustar na prévia antes.")
                return
            self.dizer(f"Recebi o áudio. Transcrevendo o ajuste do {esperando}...")
            pasta = pedidos.pasta_pedido(esperando) / "ajustes"
            pasta.mkdir(parents=True, exist_ok=True)
            n = len(list(pasta.glob("*.oga"))) + 1
            try:
                texto = transcrever(self.tg.baixar_arquivo(c["file_id"], pasta / f"{n:02d}.oga"), env=self.transcrever_env)
            except Exception as e:  # noqa: BLE001
                log.exception("transcrição do ajuste de %s", esperando)
                self.dizer(f"Não consegui transcrever o áudio ({str(e)[:120]}). Escreve o ajuste em texto, por favor.")
                return
            if not texto:
                self.dizer("Não entendi nada no áudio. Manda de novo ou escreve o ajuste.")
                return
            self.receber_ajuste(esperando, texto, "audio")
        elif tipo == "link_youtube":
            pid = pedidos.novo_pedido(url=c["url"], texto=c["texto"], etapa="aguardando_escolha")
            self.dizer(f"Recebi. Pedido {pid}.\n{mensagens.PERGUNTA_MODO}", reply_markup=mensagens.teclado_modo(pid))
        elif tipo == "comando":
            self.dizer(responder_comando(c["texto"]))
        elif tipo == "callback":
            self.clique(c)
        else:
            self.dizer("Me manda o link de um vídeo do YouTube. /ajuda mostra os comandos.")

    def clique(self, c):
        acao, _, pid = c["data"].partition(":")
        if acao in fluxo.MODOS:
            ok, texto = fluxo.escolher_modo(pid, acao)
            self._responder_clique(c, texto, mensagens.SEM_TECLADO if ok else None)
            if ok:
                self.despachar()
            self.dizer(texto)
        elif acao in ("ajustar", "manter"):
            ok, texto = (fluxo.pedir_ajuste if acao == "ajustar" else fluxo.manter)(pid)
            self._responder_clique(c, texto, mensagens.SEM_TECLADO if ok else None)
            teclado = mensagens.teclado_ajuste(pid) if acao == "ajustar" else mensagens.teclado_previa(pid)
            self.dizer(texto, **({"reply_markup": teclado} if ok else {}))
        elif acao in ("aprovar", "cancelar", "refazer"):
            if acao == "cancelar":
                ok, texto = fluxo.cancelar(pid, cliente_fn=self.cliente_fn)
            else:
                ok, texto = {"aprovar": fluxo.aprovar, "refazer": fluxo.refazer}[acao](pid)
            teclado = mensagens.teclado_cancelar(pid) if acao == "aprovar" else mensagens.SEM_TECLADO
            self._responder_clique(c, texto, teclado if ok else None)
            if ok and acao == "aprovar":
                self.acordar_envio()
            if ok and acao == "refazer":
                self.despachar()
            self.dizer(texto)
        else:
            self.tg.chamar("answerCallbackQuery", {"callback_query_id": c["id"]})

    def receber_ajuste(self, pid, texto, origem):
        ok, resposta = fluxo.ajustar(pid, texto, origem=origem)
        self.dizer(resposta)
        if ok:
            self.despachar()

    def enviar_previa(self, pedido):
        pid = pedido["pedido"]
        if pedido.get("thumb") and Path(pedido["thumb"]).exists():
            self.tg.chamar("sendPhoto", {"chat_id": self.chat_id}, arquivos={"photo": pedido["thumb"]}, timeout=120)
        r = self.tg.chamar("sendVideo", {"chat_id": self.chat_id, "supports_streaming": "true"}, arquivos={"video": pedido["previa"]}, timeout=900)
        pedidos.registrar_evento(pid, "previa_enviada", message_id=(r or {}).get("message_id"))
        self.dizer(mensagens.texto_previa(pedido), reply_markup=mensagens.teclado_previa(pid))

    def avisar(self):
        from .telegram import ErroTelegram
        avisados = set(self.estado["avisados"])
        for ev in pedidos.eventos():
            chave = self._chave(ev)
            if not ev.get("avisar") or chave in avisados:
                continue
            pedido = pedidos.estado_pedido(ev["pedido"]) or {}
            try:
                if ev["etapa"] == "aguardando_envio":
                    if pedido.get("etapa") in fluxo.PRONTOS:
                        self.enviar_previa({**pedido, **{k: ev[k] for k in ("horario", "envio_em", "previa", "thumb", "titulo") if k in ev}})
                elif ev["etapa"] == "reagendado":
                    teclado = mensagens.teclado_cancelar(ev["pedido"]) if pedido.get("aprovado_em") else mensagens.teclado_previa(ev["pedido"])
                    self.dizer(mensagens.texto_do_aviso(ev, pedido), reply_markup=teclado)
                elif ev["etapa"] == "falhou":
                    self.dizer(mensagens.texto_do_aviso(ev, pedido), reply_markup=mensagens.teclado_refazer(ev["pedido"]))
                else:
                    self.dizer(mensagens.texto_do_aviso(ev, pedido))
            except ErroTelegram as e:
                if e.codigo in (429, "rede"):
                    raise
                log.error("aviso %s perdido: %s", chave, e)
            self.estado["avisados"].append(chave)
            avisados.add(chave)
            self._salvar()
