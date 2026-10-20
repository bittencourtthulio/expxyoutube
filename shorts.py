"""Shorts do YouTube: fila de reels prontos, agendamento do dia nos slots de YT_SHORTS_SLOTS e journal.

    python3 shorts.py fila [--limite 20]
    python3 shorts.py status
    python3 shorts.py agendar [--dia AAAA-MM-DD] [--max N] [--simular]
    python3 shorts.py reconciliar <pasta> --video-id ID | --nao-subiu
    python3 shorts.py liberar <pasta>        # devolve à fila um reel que falhou ou foi excluído
    python3 shorts.py excluir <pasta>        # tira um reel da fila

Cada pasta da fonte (YT_SHORTS_DIR) com `<pasta>/<pasta>.mp4` e `legenda.txt` é um reel. `agendar` pega os
próximos reels da fila e sobe um por slot livre do DIA (privado + publishAt), até o limite da cota do dia.
Journal só por acréscimo em estado/shorts/eventos.jsonl; envio com resultado incerto trava a fila até
`reconciliar` (nunca repete upload às cegas). Autorização: .claude/rules/shorts.md.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import comum
from bot_youtube import config as _chaves
from comum import SP, UTC

RAIZ = Path(__file__).resolve().parent
ESTADO = RAIZ / "estado" / "shorts"

MAX_TITULO = 100
MAX_DESCRICAO = 5000
MAX_SEGUNDOS = 180
CUSTO_UPLOAD = 1600          # unidades de cota da Data API por videos.insert
RESERVA_COTA = 100           # folga para as leituras do próprio agendamento
CATEGORIA = "27"
SITE = "https://example.com"
PADRAO_CONFIG = {"excluir_prefixos": [], "max_total": None}
FECHADAS = {"agendado", "excluido", "falhou"}          # fora da fila até `liberar`
BLOQUEIAM = {"enviando", "verificar"}                  # resultado incerto: nada novo sobe
RAZOES_DE_PARADA = {"quotaExceeded", "dailyLimitExceeded", "uploadLimitExceeded", "rateLimitExceeded"}
RE_PEDIDO = re.compile(r"^\s*comenta\s+\S+\s+que\s+eu\s+te\s+mando\s+(?:(?:o|a|os|as|um|uma)\s+)?(.+?)\.?\s*$", re.I)
RE_CTA_INSTAGRAM = re.compile(r"^\s*(comenta|comente)\b", re.I)
RE_LINK_DE = re.compile(r"^(?:o\s+)?link\s+(?:d[oa]s?|de)\s+(?:(?:o|a|os|as)\s+)?", re.I)
PALAVRAS_SOLTAS = {"o", "a", "os", "as", "um", "uma", "de", "do", "da", "dos", "das", "em", "no", "na", "que", "e", "ou", "para",
                   "com", "por", "seu", "sua", "seus", "suas", "antes"}


class ErroShorts(Exception):
    pass


@dataclass
class Cfg:
    slots: list
    pasta: Path
    alias: str = "principal"
    canal_id: str = "UC_EXEMPLO_CONFIGURE_O_SEU"
    antecedencia_min: int = 90
    cota_dia: int = 10000


# ---------- configuração ----------

def _inteiro(valores, nome, padrao):
    bruto = valores.get(nome)
    if not bruto:
        return padrao
    try:
        return int(bruto)
    except ValueError:
        raise ErroShorts(f"{nome} precisa ser um número inteiro.") from None


def carregar_config(ambiente=None, arquivo=None):
    """Ambiente primeiro, depois o arquivo de chaves da raiz. Erro cita o nome da variável, nunca o valor de segredo."""
    ambiente = os.environ if ambiente is None else ambiente
    do_arquivo = _chaves.ler_arquivo(_chaves.ARQUIVO_CHAVES if arquivo is None else arquivo)
    v = {k: (ambiente.get(k) or do_arquivo.get(k) or "").strip() for k in _chaves.CHAVES}
    slots = [s.strip() for s in v["YT_SHORTS_SLOTS"].split(",") if s.strip()]
    if not slots:
        raise ErroShorts("Falta YT_SHORTS_SLOTS (horários do dia dos Shorts, ex.: YT_SHORTS_SLOTS=07:00,09:30,12:00,15:00,18:00,21:00).")
    ruins = [s for s in slots if not _chaves.RE_HORA.match(s)]
    if ruins:
        raise ErroShorts(f"YT_SHORTS_SLOTS tem horário inválido: {', '.join(ruins)} (use HH:MM de 00:00 a 23:59).")
    pasta = Path(v["YT_SHORTS_DIR"]).expanduser() if v["YT_SHORTS_DIR"] else RAIZ / "midias" / "shorts"
    cfg = Cfg(slots=sorted(set(slots)), pasta=pasta, antecedencia_min=_inteiro(v, "YT_ANTECEDENCIA_MIN", 90),
              cota_dia=_inteiro(v, "YT_COTA_DIA", 10000))
    if v["YT_CANAL_ALIAS"]:
        cfg.alias = v["YT_CANAL_ALIAS"]
    if v["YT_CANAL_ID"]:
        cfg.canal_id = v["YT_CANAL_ID"]
    return cfg


def ler_ajustes():
    """estado/shorts/config.json: excluir_prefixos (pastas que não entram) e max_total (teto de Shorts agendados, null = sem teto)."""
    dados = comum.ler_json(ESTADO / "config.json", {}) or {}
    return {**PADRAO_CONFIG, **{k: dados[k] for k in PADRAO_CONFIG if k in dados}}


# ---------- texto público do Short ----------

def _limpar(texto):
    return re.sub(r"\s+", " ", str(texto).replace("<", "").replace(">", "")).strip()


def _sem_acento(texto):
    return unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower()


def titulo_de(legenda, assunto=""):
    """Título do Short: o tema da primeira linha da legenda ("Comenta X que eu te mando <tema>."), até 100 caracteres."""
    linhas = [ln.strip() for ln in legenda.splitlines() if ln.strip()]
    bruto = ""
    if linhas:
        achou = RE_PEDIDO.match(linhas[0])
        bruto = achou.group(1) if achou else ""
    if len(bruto) < 15:
        base = next((ln for ln in linhas if not ln.startswith(("→", "#")) and not RE_CTA_INSTAGRAM.match(ln)), assunto or "")
        bruto = re.split(r"(?<=[.!?])\s", base)[0] if base else (assunto or "")
    bruto = RE_LINK_DE.sub("", _limpar(bruto)).rstrip(".")
    titulo = bruto[:1].upper() + bruto[1:]
    if len(titulo) > MAX_TITULO:
        titulo = titulo[:MAX_TITULO + 1].rsplit(" ", 1)[0]
        palavras = titulo.split()
        while len(palavras) > 3 and palavras[-1].lower().strip(",;:-") in PALAVRAS_SOLTAS:
            palavras.pop()
        titulo = " ".join(palavras).rstrip(",;:- ")
    return titulo


def descricao_de(legenda):
    """Legenda do reel sem a chamada de comentário do Instagram, com o CTA do Seu Site e #Shorts no fim."""
    linhas = [ln.rstrip() for ln in legenda.replace("\r\n", "\n").splitlines() if not RE_CTA_INSTAGRAM.match(ln)]
    hashtags = [ln.strip() for ln in linhas if ln.strip() and all(t.startswith("#") for t in ln.split())]
    corpo = [ln for ln in linhas if ln.strip() not in hashtags]
    texto = re.sub(r"\n{3,}", "\n\n", "\n".join(corpo)).replace("<", "").replace(">", "").strip()
    rodape = f"Aulas de IA e programação: {SITE}\n\n" + " ".join(hashtags + ["#Shorts"])
    return (texto[:MAX_DESCRICAO - len(rodape) - 2].rstrip() + "\n\n" + rodape).strip()


def proibidos(titulo, descricao):
    """Onde "recriação" aparece no texto público (Usuário, 28/09/2026: nunca, em lugar nenhum)."""
    return [onde for onde, t in (("título", titulo), ("descrição", descricao)) if "recria" in _sem_acento(t)]


def metadados(reel):
    legenda = reel["legenda"].read_text(encoding="utf-8")
    titulo, descricao = titulo_de(legenda, reel.get("assunto", "")), descricao_de(legenda)
    if len(titulo) < 5:
        raise ValueError("não consegui tirar um título da legenda")
    achados = proibidos(titulo, descricao)
    if achados:
        raise ValueError(f"a palavra recriação aparece em {', '.join(achados)}")
    return {"chave": reel["chave"], "titulo": titulo, "descricao": descricao, "mp4": reel["mp4"]}


# ---------- vídeo ----------

def sondar(video, rodar=subprocess.run):
    saida = rodar(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(video)],
                  capture_output=True, text=True, timeout=60)
    if saida.returncode != 0:
        raise ValueError("o ffprobe não conseguiu ler o vídeo")
    dados = json.loads(saida.stdout)
    video_st = next((s for s in dados.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video_st:
        raise ValueError("o arquivo não tem faixa de vídeo")
    return {"largura": int(video_st.get("width") or 0), "altura": int(video_st.get("height") or 0),
            "duracao": float((dados.get("format") or {}).get("duration") or 0),
            "audio": any(s.get("codec_type") == "audio" for s in dados["streams"])}


def validar_video(info):
    """Short = vertical (ou quadrado), até 3 minutos, com áudio."""
    if info["largura"] <= 0 or info["altura"] < info["largura"]:
        raise ValueError(f"o Short precisa ser vertical; este é {info['largura']}x{info['altura']}")
    if not 0 < info["duracao"] <= MAX_SEGUNDOS:
        raise ValueError(f"duração {info['duracao']:.0f}s fora do limite de Short (até {MAX_SEGUNDOS}s)")
    if not info["audio"]:
        raise ValueError("o vídeo não tem áudio")


# ---------- fila ----------

def listar_reels(pasta, excluir_prefixos=()):
    """Reels prontos: `<pasta>/<pasta>.mp4` com `legenda.txt`, do mais novo para o mais antigo."""
    raiz = Path(pasta)
    if not raiz.is_dir():
        raise ErroShorts(f"a pasta dos reels não existe: {raiz}")
    reels = []
    for d in raiz.iterdir():
        mp4, legenda = d / f"{d.name}.mp4", d / "legenda.txt"
        if not d.is_dir() or d.name.startswith(tuple(excluir_prefixos)) or not mp4.is_file() or not legenda.is_file():
            continue
        publicacao = comum.ler_json(d / "publicacao.json", {}) or {}
        reels.append({"chave": d.name, "mp4": mp4, "legenda": legenda, "mtime": mp4.stat().st_mtime,
                      "assunto": str(publicacao.get("assunto") or "")})
    return sorted(reels, key=lambda r: (-r["mtime"], r["chave"]))


def eventos():
    return comum.ler_jsonl(ESTADO / "eventos.jsonl")[0]


def registrar(chave, etapa, **campos):
    comum.anexar_jsonl(ESTADO / "eventos.jsonl", {"chave": chave, "etapa": etapa, "em": comum.agora_iso(), **campos})


def situacao():
    """Último evento de cada reel."""
    return {e["chave"]: e for e in eventos() if e.get("chave")}


def fila(cfg, ajustes=None):
    """Reels ainda não usados, sem título repetido (a mesma pauta gravada duas vezes sobe uma vez)."""
    ajustes = ajustes or ler_ajustes()
    usados = situacao()
    titulos = {_sem_acento(e.get("titulo")) for e in usados.values() if e["etapa"] == "agendado" and e.get("titulo")}
    saida = []
    for reel in listar_reels(cfg.pasta, ajustes["excluir_prefixos"]):
        if usados.get(reel["chave"], {}).get("etapa") in FECHADAS | BLOQUEIAM:
            continue
        titulo = titulo_de(reel["legenda"].read_text(encoding="utf-8"), reel["assunto"])
        if _sem_acento(titulo) in titulos:
            continue
        titulos.add(_sem_acento(titulo))
        saida.append(reel)
    return saida


# ---------- horários e cota ----------

def slots_livres(dia, horarios, agora, antecedencia_min, tomadas):
    piso = agora + timedelta(minutes=antecedencia_min)
    livres = []
    for h in sorted(horarios):
        hh, mm = map(int, h.split(":"))
        candidato = datetime(dia.year, dia.month, dia.day, hh, mm, tzinfo=SP)
        if candidato >= piso and h not in tomadas:
            livres.append(candidato)
    return livres


def horas_tomadas(dia, agendados):
    """HH:MM já ocupadas no dia: publishAt de qualquer vídeo agendado no canal e Shorts do nosso journal."""
    horas = {h.astimezone(SP).strftime("%H:%M") for h in agendados if h.astimezone(SP).date() == dia}
    for e in situacao().values():
        if e["etapa"] in ("agendado", "enviando", "verificar") and str(e.get("horario", ""))[:10] == dia.isoformat():
            horas.add(e["horario"][11:16])
    return horas


def cota_usada(cliente, agora):
    dia = comum.hoje_pacifico(agora.astimezone(UTC))
    return int(((comum.ler_json(Path(cliente.raiz) / "estado" / "cota.json", {}) or {}).get(dia) or {}).get("data") or 0)


# ---------- YouTube ----------

def conferir_canal(cliente, cfg):
    canais = cliente._executa("data", cliente.data.channels().list(part="id", mine=True)).get("items") or []
    if len(canais) != 1 or canais[0]["id"] != cfg.canal_id:
        raise ErroShorts("o canal autenticado difere do canal autorizado; nenhuma escrita foi feita")


def subir(cliente, meta, publish_at):
    """videos.insert já privado e com publishAt. Devolve o id do vídeo."""
    import yt
    from googleapiclient.http import MediaFileUpload
    corpo = {"snippet": {"title": meta["titulo"], "description": meta["descricao"], "categoryId": CATEGORIA,
                         "defaultLanguage": "pt-BR", "defaultAudioLanguage": "pt-BR"},
             "status": {"privacyStatus": "private", "publishAt": publish_at, "selfDeclaredMadeForKids": False,
                        "containsSyntheticMedia": True, "embeddable": True, "publicStatsViewable": True}}
    pedido = cliente.data.videos().insert(part="snippet,status", notifySubscribers=False, body=corpo,
                                          media_body=MediaFileUpload(str(meta["mp4"]), mimetype="video/mp4",
                                                                     chunksize=8 * 1024 * 1024, resumable=True))
    resposta = None
    while resposta is None:
        try:
            _, resposta = pedido.next_chunk(num_retries=3)
        except Exception as erro:  # noqa: BLE001 - traduzido, sem imprimir URL de upload
            raise (yt._traduz(erro) or erro) from erro
    return resposta["id"]


def _sha256(caminho):
    h = hashlib.sha256()
    with Path(caminho).open("rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def _utc(instante):
    return instante.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _status_do_video(cliente, video_id):
    itens = cliente._executa("data", cliente.data.videos().list(part="status,snippet", id=video_id)).get("items") or []
    return itens[0] if itens else None


# ---------- agendar ----------

def agendar(cfg, agora=None, dia=None, maximo=None, simular=False, cliente=None, enviar=None, sonda=None):
    import yt
    from bot_youtube import canal as _canal
    agora = (agora or datetime.now(SP)).astimezone(SP)
    dia = dia or agora.date()
    enviar, sonda = enviar or subir, sonda or sondar
    trancados = sorted(c for c, e in situacao().items() if e["etapa"] in BLOQUEIAM)
    if trancados:
        raise ErroShorts(f"envio com resultado incerto em {', '.join(trancados)}: confira no Studio e rode "
                         "`python3 shorts.py reconciliar <pasta> --video-id ID` ou `--nao-subiu` antes de agendar")
    ajustes = ler_ajustes()
    cliente = cliente or yt.Cliente.conectar(cfg.alias)
    conferir_canal(cliente, cfg)
    livres = slots_livres(dia, cfg.slots, agora, cfg.antecedencia_min, horas_tomadas(dia, _canal.agendados(cliente)))
    relato = {"dia": dia.isoformat(), "simulado": simular, "slots_livres": len(livres), "agendados": [], "pulados": [], "avisos": []}
    if maximo is not None:
        livres = livres[:max(0, maximo)]
    if ajustes["max_total"] is not None:
        restante = int(ajustes["max_total"]) - sum(1 for e in situacao().values() if e["etapa"] == "agendado")
        if restante < len(livres):
            relato["avisos"].append(f"teto de {ajustes['max_total']} Shorts (estado/shorts/config.json): {max(0, restante)} vaga(s) restante(s)")
            livres = livres[:max(0, restante)]
    cabem = max(0, (cfg.cota_dia - cota_usada(cliente, agora) - RESERVA_COTA) // CUSTO_UPLOAD)
    if cabem < len(livres):
        relato["avisos"].append(f"cota do dia: cabem {cabem} upload(s) de {CUSTO_UPLOAD} unidades")
        livres = livres[:cabem]
    pendentes = fila(cfg, ajustes)
    relato["na_fila"] = len(pendentes)
    for slot in livres:
        publicado = None
        while pendentes and publicado is None:
            reel = pendentes.pop(0)
            try:
                meta = metadados(reel)
                validar_video(sonda(reel["mp4"]))
            except ValueError as erro:
                relato["pulados"].append({"chave": reel["chave"], "motivo": str(erro)})
                if not simular:
                    registrar(reel["chave"], "falhou", motivo=str(erro))
                continue
            publicado = (reel, meta)
        if publicado is None:
            relato["avisos"].append("a fila acabou antes de preencher todos os slots")
            break
        reel, meta = publicado
        horario = slot.isoformat(timespec="seconds")
        if simular:
            relato["agendados"].append({"chave": reel["chave"], "titulo": meta["titulo"], "horario": horario})
            continue
        registrar(reel["chave"], "enviando", horario=horario, titulo=meta["titulo"])
        cliente._conta("data", CUSTO_UPLOAD)
        try:
            video_id = enviar(cliente, meta, _utc(slot))
        except yt.ErroAuth as erro:
            registrar(reel["chave"], "liberado", nota="login expirado antes do envio")
            relato["erro"] = f"{erro}"
            return relato
        except yt.ErroAPI as erro:
            if erro.razao in RAZOES_DE_PARADA:
                registrar(reel["chave"], "liberado", nota=f"o YouTube recusou por limite ({erro.razao}); nada subiu")
                relato["avisos"].append(f"parei: {erro.razao}. A cota zera à meia-noite do Pacífico")
                return relato
            if 400 <= erro.status < 500:
                registrar(reel["chave"], "falhou", motivo=str(erro)[:300])
                relato["pulados"].append({"chave": reel["chave"], "motivo": str(erro)[:200]})
                continue
            relato["erro"] = f"resultado incerto em {reel['chave']} ({str(erro)[:150]}); reconciliar antes de repetir"
            return relato
        except Exception as erro:  # noqa: BLE001 - upload interrompido: pode ter subido, nunca repetir às cegas
            relato["erro"] = f"resultado incerto em {reel['chave']} ({type(erro).__name__}); reconciliar antes de repetir"
            return relato
        video = _status_do_video(cliente, video_id)
        status = (video or {}).get("status") or {}
        if status.get("privacyStatus") != "private" or status.get("publishAt") != _utc(slot):
            registrar(reel["chave"], "verificar", video_id=video_id, horario=horario, titulo=meta["titulo"])
            relato["erro"] = f"o vídeo {video_id} subiu, mas o agendamento não foi confirmado; reconciliar"
            return relato
        registrar(reel["chave"], "agendado", video_id=video_id, horario=horario, publish_at=_utc(slot), titulo=meta["titulo"],
                  sha256=_sha256(reel["mp4"]))
        relato["agendados"].append({"chave": reel["chave"], "titulo": meta["titulo"], "horario": horario, "video_id": video_id})
    return relato


# ---------- manutenção ----------

def reconciliar(cfg, chave, video_id=None, nao_subiu=False, cliente=None):
    import yt
    atual = situacao().get(chave)
    if not atual or atual["etapa"] not in BLOQUEIAM:
        raise ErroShorts(f"{chave} não está com envio incerto")
    if bool(video_id) == bool(nao_subiu):
        raise ErroShorts("informe --video-id ID ou --nao-subiu")
    if nao_subiu:
        registrar(chave, "liberado", nota="Usuário confirmou no Studio que o vídeo não subiu")
        return {"chave": chave, "resultado": "de volta à fila"}
    cliente = cliente or yt.Cliente.conectar(cfg.alias)
    conferir_canal(cliente, cfg)
    video = _status_do_video(cliente, video_id)
    if not video or video["snippet"].get("channelId") != cfg.canal_id:
        raise ErroShorts(f"o vídeo {video_id} não está no canal autorizado")
    publish_at = video["status"].get("publishAt")
    registrar(chave, "agendado", video_id=video_id, publish_at=publish_at, horario=atual.get("horario"),
              titulo=video["snippet"].get("title"), privacidade=video["status"].get("privacyStatus"), nota="reconciliado")
    return {"chave": chave, "resultado": "agendado", "video_id": video_id, "publish_at": publish_at}


def liberar(chave):
    atual = situacao().get(chave)
    if not atual or atual["etapa"] not in ("falhou", "excluido"):
        raise ErroShorts(f"{chave} não está falhado nem excluído")
    registrar(chave, "liberado", nota="devolvido à fila")
    return {"chave": chave, "resultado": "de volta à fila"}


def excluir(chave):
    registrar(chave, "excluido", nota="tirado da fila")
    return {"chave": chave, "resultado": "excluído"}


def resumo(cfg):
    estado = situacao()
    contagem = {}
    for e in estado.values():
        contagem[e["etapa"]] = contagem.get(e["etapa"], 0) + 1
    proximos = sorted((e["horario"], e.get("titulo")) for e in estado.values() if e["etapa"] == "agendado" and e.get("horario", "") > comum.agora_iso())
    ajustes = ler_ajustes()
    return {"na_fila": len(fila(cfg, ajustes)), "eventos_por_etapa": contagem, "ajustes": ajustes, "slots": cfg.slots,
            "proximos_agendados": proximos[:10], "travados": sorted(c for c, e in estado.items() if e["etapa"] in BLOQUEIAM),
            "falhados": sorted(c for c, e in estado.items() if e["etapa"] == "falhou")}


# ---------- linha de comando ----------

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fila")
    f.add_argument("--limite", type=int, default=20)
    sub.add_parser("status")
    a = sub.add_parser("agendar")
    a.add_argument("--dia", help="AAAA-MM-DD (padrão: hoje, fuso de São Paulo)")
    a.add_argument("--max", type=int, dest="maximo")
    a.add_argument("--simular", action="store_true")
    r = sub.add_parser("reconciliar")
    r.add_argument("chave")
    r.add_argument("--video-id")
    r.add_argument("--nao-subiu", action="store_true")
    sub.add_parser("liberar").add_argument("chave")
    sub.add_parser("excluir").add_argument("chave")
    args = p.parse_args(argv)
    try:
        cfg = carregar_config()
        if args.cmd == "fila":
            reels = fila(cfg)
            saida = {"total": len(reels), "proximos": [{"chave": r_["chave"], "titulo": titulo_de(r_["legenda"].read_text(encoding="utf-8"), r_["assunto"])}
                                                       for r_ in reels[:args.limite]]}
        elif args.cmd == "status":
            saida = resumo(cfg)
        elif args.cmd == "agendar":
            ESTADO.mkdir(parents=True, exist_ok=True)
            with (ESTADO / "agendar.lock").open("a") as trava:
                try:
                    fcntl.flock(trava, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise ErroShorts("outro agendamento de Shorts está rodando; nada a fazer") from None
                dia = datetime.strptime(args.dia, "%Y-%m-%d").date() if args.dia else None
                saida = agendar(cfg, dia=dia, maximo=args.maximo, simular=args.simular)
        elif args.cmd == "reconciliar":
            saida = reconciliar(cfg, args.chave, video_id=args.video_id, nao_subiu=args.nao_subiu)
        elif args.cmd == "liberar":
            saida = liberar(args.chave)
        else:
            saida = excluir(args.chave)
    except (ErroShorts, ValueError) as erro:
        print(json.dumps({"ok": False, "error": str(erro)}, ensure_ascii=False))
        return 1
    except Exception as erro:  # noqa: BLE001 - sem payload nem URL de biblioteca externa
        nome = type(erro).__name__
        print(json.dumps({"ok": False, "error": f"{nome}: {str(erro)[:200]}"}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": "erro" not in saida, **saida}, ensure_ascii=False, indent=2))
    return 1 if "erro" in saida else 0


if __name__ == "__main__":
    sys.exit(main())
