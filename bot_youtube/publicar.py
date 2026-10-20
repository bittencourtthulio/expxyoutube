"""Subir e agendar o vídeo de um pedido pelo publicacao.py do squad (Data API, journal idempotente por pedido).

A autorização é o link que o Usuário mandou ao bot mais o Aprovar ou o prazo de 1 h antes do slot (D-03, D-04):
fica escrita no campo `authorization` do plano. Antes de subir, o bot registra a revisão `entrega` da aula (D-32).
"""
import json
import os
import sys
import unicodedata
from pathlib import Path

from . import executar as _executar
from . import pedidos

RAIZ = Path(__file__).resolve().parent.parent
PUBLICACAO = RAIZ / "publicacao.py"


def _rel(destino, base):
    return os.path.relpath(Path(destino).resolve(), Path(base).resolve())


def recriacao(pid):
    return json.loads((pedidos.pasta_pedido(pid) / "recriacao.json").read_text(encoding="utf-8"))


def _tem_recriacao(texto):
    limpo = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower()
    return "recria" in limpo


def _ler(caminho):
    try:
        return Path(caminho).read_text(encoding="utf-8")
    except (OSError, TypeError):
        return ""


def termos_proibidos(rec, cfg):
    """Onde "recriação" aparece em algo público do vídeo (Usuário, 28/09/2026: nunca, em lugar nenhum).
    Confere título, playlist, descrição, legenda, thumbs.json e o nome da série no aula.json (vai no vídeo)."""
    achados = []
    playlist = rec.get("playlist") or {}
    textos = {"titulo": rec.get("titulo"), "playlist": f"{playlist.get('title', '')} {playlist.get('description', '')}",
              "descricao": _ler(rec.get("descricao")), "aula.srt": _ler(rec.get("srt"))}
    try:   # da thumb, só o que aparece: título e manchete de cada variante
        variantes = json.loads(_ler(rec.get("thumbs")) or "{}").get("variants") or []
        textos["thumbs.json"] = " ".join(f"{v.get('title', '')} {v.get('headline', '')}" for v in variantes)
    except ValueError:
        pass
    if rec.get("aula"):
        try:
            textos["aula.json (série)"] = json.loads(_ler(Path(cfg.cursos_ia) / rec["aula"] / "src/aula.json") or "{}").get("serie")
        except ValueError:
            pass
    for onde, texto in textos.items():
        if _tem_recriacao(texto):
            achados.append(onde)
    return achados


def plano(e, cfg, motivo="prazo sem resposta"):
    pid = e["pedido"]
    pasta = pedidos.pasta_pedido(pid)
    rec = recriacao(pid)
    playlist = dict(rec.get("playlist") or {})
    if not playlist.get("id") and playlist.get("title") and not playlist.get("description"):
        playlist["description"] = f"Aulas sobre {playlist['title']}."
    return {
        "alias": cfg.canal_alias, "channel_id": cfg.canal_id,
        "publish_local": e["horario"], "timezone": "America/Sao_Paulo",
        "authorization": (f"Bot do YouTube (Telegram): pedido {pid}, link enviado pelo Usuário ({e.get('url')}); {motivo}. "
                          "Regra D-03/D-04 de ../cursos-ia/docs/bot-telegram-youtube e .claude/rules/bot-youtube.md."),
        "made_for_kids": False, "contains_synthetic_media": True, "language": "pt-BR", "category_id": 27,
        "notify_subscribers": True, "ab_test": False,
        "video": _rel(rec["video"], pasta), "description": _rel(rec["descricao"], pasta),
        "captions": _rel(rec["srt"], pasta), "thumbs": _rel(rec["thumbs"], pasta), "playlist": playlist,
    }


def gravar_plano(e, cfg, motivo="prazo sem resposta"):
    arq = pedidos.pasta_pedido(e["pedido"]) / "plano-publicacao.json"
    arq.write_text(json.dumps(plano(e, cfg, motivo), ensure_ascii=False, indent=2), encoding="utf-8")
    return arq


def _rodar_padrao(cmd, timeout=None, cwd=None, env=None):
    return _executar.rodar(cmd, timeout=timeout, cwd=cwd, env=env)


def _agendado(journal):
    try:
        dados = json.loads(journal.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, None
    done = dados.get("done") or {}
    return done, dados.get("pending")


def _auth(saida):
    return "refaça o login" in saida or "credencial" in saida.lower() and "expirad" in saida.lower()


def enviar(pid, cfg, executar=None, motivo="prazo sem resposta"):
    rodar = executar or _rodar_padrao
    e = pedidos.estado_pedido(pid)
    pasta = pedidos.pasta_pedido(pid)
    journal = pasta / "publicacao-estado.json"
    done, _ = _agendado(journal)
    if done and (done.get("scheduled") or {}).get("publishAt"):
        pedidos.registrar_evento(pid, "enviado", avisar=True, video_id=done.get("video_id"),
                                 publish_at=done["scheduled"]["publishAt"], nota="journal já mostrava o vídeo agendado: não subi de novo")
        return "enviado"
    proibidos = termos_proibidos(recriacao(pid), cfg)
    if proibidos:
        pedidos.registrar_evento(pid, "falhou", avisar=True,
                                 nota=f"não subi: a palavra recriação aparece em {', '.join(proibidos)}; cada série tem nome próprio e "
                                      "recriação não pode aparecer em lugar nenhum. Ajuste e mande Refazer")
        return "falhou"
    pedidos.registrar_evento(pid, "enviando", avisar=False)
    aula = Path(cfg.cursos_ia) / e["aula"] if e.get("aula") else None
    if aula:
        codigo, saida = rodar(["python3", str(Path(cfg.cursos_ia) / "kit-gravacao/produzir_aula.py"), "revisar", str(aula), "--etapa", "entrega",
                               "--revisor", "telegram", "--observacao", f"pedido {pid} do bot do YouTube: {motivo}"], timeout=600, cwd=str(cfg.cursos_ia))
        if codigo != 0:
            pedidos.registrar_evento(pid, "falhou", avisar=True, nota=f"a revisão de entrega da aula recusou: {saida.strip()[-300:]}")
            return "falhou"
    arq = gravar_plano(e, cfg, motivo)
    codigo, saida = rodar([sys.executable, str(PUBLICACAO), "validar", str(arq)], timeout=600, cwd=str(RAIZ))
    if codigo != 0:
        pedidos.registrar_evento(pid, "falhou", avisar=True, nota=f"o validar do publicacao.py recusou: {saida.strip()[-300:]}")
        return "falhou"
    codigo, saida = rodar([sys.executable, str(PUBLICACAO), "enviar", str(arq), "--state", str(journal)], timeout=3600, cwd=str(RAIZ))
    done, pendente = _agendado(journal)
    if codigo in (0, 2) and done and done.get("video_id"):
        publish_at = (done.get("scheduled") or {}).get("publishAt")
        nota = None if codigo == 0 else "agendado; a verificação final ainda tem checagens pendentes (processamento do YouTube)"
        pedidos.registrar_evento(pid, "enviado", avisar=True, video_id=done["video_id"], publish_at=publish_at, nota=nota)
        return "enviado"
    if _auth(saida):
        pedidos.registrar_evento(pid, "bloqueado", avisar=True,
                                 nota=f"o login do canal {cfg.canal_alias} expirou: rode no youtube-squad `.venv/bin/python auth.py {cfg.canal_alias}` e depois Refazer")
        return "bloqueado"
    if pendente:
        pedidos.registrar_evento(pid, "falhou", avisar=True,
                                 nota=f"o envio parou no passo '{pendente}' com resultado incerto: reconciliar o journal {journal.name} no Studio antes de repetir")
        return "falhou"
    pedidos.registrar_evento(pid, "falhou", avisar=True, nota=f"o publicacao.py não agendou (código {codigo}): {saida.strip()[-300:]}")
    return "falhou"
