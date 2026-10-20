"""Cérebro de boas práticas de YouTube: o que criadores ensinam sobre crescer no YouTube vira nota com frontmatter.

Este script faz a parte que não pede leitura: cadastra canal, descobre vídeo novo, baixa a
legenda e grava uma nota `bruto` em cerebro/videos/<canal>/. Quem lê a transcrição e escreve
resumo, boas práticas e ressalvas é o agente `curador` (skill `cerebro-youtube`), que
então marca a nota como `destilado`.

  python3 cerebro.py canal add https://www.youtube.com/@canal --previa     # confere nome e títulos, não grava nada
  python3 cerebro.py canal add https://www.youtube.com/@canal [--id slug] [--desde 2025-01-01] [--shorts] [--lives]
  python3 cerebro.py canal pausar <canal>          # e `canal ativar <canal>`; `canal remover <canal>` só para canal sem nota
  python3 cerebro.py canais                        # canais, o que já entrou, último vídeo de cada um
  python3 cerebro.py importar <canal> [--limite 50] [--desde 2025-01-01]   # tudo o que o canal já tem
  python3 cerebro.py importar <canal> --video <id>   # um vídeo só, inclusive um que tinha sido descartado
  python3 cerebro.py varrer [canal] [--ultimos 30] # rotina diária: só o que é novo, em todos os canais ativos
  python3 cerebro.py pendentes [--limite 20]       # notas que ainda são `bruto`, mais novas primeiro
  python3 cerebro.py buscar --tema miniatura [--texto "..."] [--canal x] [--desde data] [--praticas]
  python3 cerebro.py indice                        # regrava cerebro/INDEX.md
  python3 cerebro.py validar                       # frontmatter, temas e seções das notas destiladas
  python3 cerebro.py status

O que já entrou é derivado do disco (o frontmatter das notas). `estado/cerebro.json` guarda o
resto: o último vídeo de cada canal, a última varredura, o que espera legenda e o que foi
descartado. Importação interrompida continua de onde parou: é só rodar de novo.
Todo comando aceita --json.
"""
import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
import unicodedata
import urllib.request
from datetime import date, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
# O que muda de uma base para outra. `biblioteca.py` roda este mesmo motor com outra BASE (ver `usar_base`):
# `id` é a pasta, o script e o arquivo de estado; `secao_itens` é a seção que o destilador escreve e marca com [tema];
# `itens` é a opção do `buscar` que traz essa seção, e a chave dela na saída.
BASE = {"id": "cerebro", "nome": "o cérebro", "onde": "no cérebro", "titulo": "Cérebro de YouTube",
        "secao_itens": "Boas práticas", "item": "prática", "itens": "praticas", "descricao": __doc__}


def globais_da_base(base, raiz):
    pasta = raiz / base["id"]
    return {"BASE": base, "PASTA": pasta, "CANAIS": pasta / "canais.json", "TEMAS": pasta / "temas.json", "VIDEOS": pasta / "videos",
            "INDICE": pasta / "INDEX.md", "ESTADO": raiz / "estado" / f"{base['id']}.json",
            "SECOES_DESTILADAS": ("Resumo", base["secao_itens"], "Ressalvas")}


def usar_base(base):
    """Um processo, uma base: o script de cada base chama isto uma vez, antes do `main`."""
    globals().update(globais_da_base(base, RAIZ))


usar_base(BASE)  # define PASTA, CANAIS, TEMAS, VIDEOS, INDICE, ESTADO e SECOES_DESTILADAS

PENDENTE = "_pendente de destilação_"
SEM_COMENTARIO = re.compile(r"(^|\s+)#.*$")
RELEVANCIAS = ("alta", "media", "baixa", "fora")
CORTE = "anterior ao corte"  # motivo de descarte que some quando o corte do canal muda
ABAS = {"videos": "videos", "shorts": "shorts", "lives": "streams"}
ESPERA_LEGENDA_DIAS = 3   # vídeo mais novo que isso e sem legenda: a automática ainda pode chegar
MAX_TENTATIVAS = 7        # depois disso o vídeo sai da fila de espera e vai para os descartados
TENTATIVAS_LISTAGEM = 3
RECUOS = (90, 180, 360)      # bloqueio do YouTube é por ritmo e passa em minutos: espera e insiste antes de largar a rodada
FALHAS_SEGUIDAS = 3       # tantas falhas de rede em sequência: o problema é a rede ou o YouTube, não o vídeo. Para a rodada.
CAMPOS = ("id", "titulo", "canal", "canal_nome", "url", "publicado_em", "ingerido_em", "duracao_seg", "idioma",
          "legenda", "visualizacoes", "transcricao_sha", "status", "relevancia", "temas", "destilado_em")
# só isto é definitivo; qualquer outro erro do YouTube é tratado como passageiro e o vídeo é tentado de novo
PERMANENTE = re.compile(r"private video|video (is )?(unavailable|not available)|has been removed|members[- ]only|join this channel|account .*terminated|"
                        r"confirm your age|not available in your country|copyright", re.I)
BLOQUEIO = re.compile(r"HTTP Error 429|Too Many Requests|confirm you.re not a bot", re.I)


class SemLegenda(Exception):
    def __init__(self, motivo, publicado_em=None):
        super().__init__(motivo)
        self.publicado_em = publicado_em


class Indisponivel(Exception):
    """Definitivo: vídeo privado, removido, só para membros."""


class Passageiro(Exception):
    """Rede, extractor quebrado, estreia que ainda não foi ao ar: tentar de novo, nunca descartar."""


class LimiteDeTaxa(Exception):
    pass


# ---------- arquivos ----------

def hoje():
    return date.today().isoformat()


def ler_json(arq, padrao):
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else padrao


def gravar_json(arq, dados):
    """Grava num temporário e troca: um processo morto no meio não deixa JSON pela metade."""
    arq.parent.mkdir(parents=True, exist_ok=True)
    tmp = arq.with_name(arq.name + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, arq)


def carregar_canais():
    return ler_json(CANAIS, {"canais": []})["canais"]


def salvar_canais(canais):
    gravar_json(CANAIS, {"_": f"Canais que alimentam {BASE['nome']}. Cadastre com `python3 {BASE['id']}.py canal add <url>`.", "canais": canais})


def carregar_estado():
    return ler_json(ESTADO, {"canais": {}})


def estado_do_canal(estado, cid):
    return estado["canais"].setdefault(cid, {"ultimo_video": None, "ultima_varredura": None, "aguardando": {}, "descartados": {}})


def salvar_estado_do_canal(cid, est):
    """Relê o arquivo e troca só este canal: outra rodada (o cron, um `importar` longo) pode ter gravado os outros."""
    estado = carregar_estado()
    estado["canais"][cid] = est
    gravar_json(ESTADO, estado)


def temas_validos():
    return [t["id"] for t in ler_json(TEMAS, {"temas": []})["temas"]]


def achar_canal(canais, ref):
    for c in canais:
        if ref in (c["id"], c["url"], c.get("channel_id")):
            return c
    raise SystemExit(f"canal '{ref}' não está cadastrado. Cadastrados: {', '.join(c['id'] for c in canais) or 'nenhum'}.")


def slug(texto, limite=60):
    limpo = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", limpo.lower()).strip("-")[:limite].strip("-")


def sha(texto):
    return hashlib.sha256(texto.strip().encode("utf-8")).hexdigest()[:12]


# ---------- notas (frontmatter + corpo) ----------

def ler_nota(arq):
    """Frontmatter no formato que este script grava: `chave: <valor em JSON>`, que também é YAML válido."""
    texto = arq.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    if not texto.startswith("---\n") or "\n---\n" not in texto[4:]:
        raise ValueError("sem frontmatter")
    cabeca, corpo = texto[4:].split("\n---\n", 1)
    return ler_cabeca(cabeca.splitlines()), corpo


def ler_cabeca(linhas):
    """As linhas do frontmatter viram dicionário. Quem destila edita à mão, então lista solta (`[a, b]`) e
    lista em bloco também entram, e `temas` sai sempre como lista: quem consome itera, e texto iterado vira
    letra avulsa. É a única leitura de frontmatter do repositório, inclusive a do grafo do painel; leitor que
    repetisse o `json.loads` sem esta tolerância transformaria `[modelos, infra]` em nós `m`, `o`, `d`, `e`.
    `_temas_fora_do_formato` marca a nota cuja linha não é o JSON que o script grava, para o `validar` cobrar."""
    meta, ultima, temas_em_json = {}, None, True
    for linha in linhas:
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        if linha.lstrip().startswith("- ") and ultima:  # lista YAML em bloco, escrita à mão
            meta[ultima] = [*(meta[ultima] if isinstance(meta[ultima], list) else []), valor_do_campo(linha.lstrip()[2:])]
            continue
        chave, _, valor = linha.partition(":")
        ultima = chave.strip()
        meta[ultima] = valor_do_campo(valor)
        if ultima == "temas":
            temas_em_json = veio_em_json(valor)
    if "temas" in meta:
        meta["temas"] = meta["temas"] if isinstance(meta["temas"], list) else [meta["temas"]] if meta["temas"] else []
        if not temas_em_json:
            meta["_temas_fora_do_formato"] = True
    return meta


def veio_em_json(valor):
    """A linha está no JSON que o script grava? Vale para `temas`, onde YAML escrito à mão custa caro: lista
    em bloco e campo vazio somem virando lista vazia, mas `[a, b]` chega como texto e quem itera vê letras.
    `ler_cabeca` entende as três; o `validar` é que mantém um formato só no disco, para o leitor de amanhã."""
    valor = valor.strip()
    if valor in ("", "~"):                       # vira lista vazia em qualquer leitor: não há o que divergir
        return True
    for tentativa in (valor, SEM_COMENTARIO.sub("", valor).strip()):
        try:
            json.loads(tentativa)
            return True
        except json.JSONDecodeError:
            pass
    return False


def valor_do_campo(valor):
    """O script grava JSON, mas quem destila edita à mão: aceita YAML simples (`[a, b]`, texto sem aspas, vazio, `# comentário`)."""
    valor = valor.strip()
    sem_comentario = SEM_COMENTARIO.sub("", valor).strip()
    for tentativa in (valor, sem_comentario):
        try:
            return json.loads(tentativa)
        except json.JSONDecodeError:
            pass
    valor = sem_comentario
    if valor in ("", "~"):
        return None
    if valor.startswith("[") and valor.endswith("]"):
        return [v.strip().strip("\"'") for v in valor[1:-1].split(",") if v.strip()]
    return valor.strip("\"'")


def notas(canal=None):
    """Notas legíveis. Arquivo quebrado não derruba a rotina: é pulado com aviso, e quem reprova é o `validar`."""
    base = VIDEOS / canal if canal else VIDEOS
    achadas = []
    for arq in sorted(base.rglob("*.md")) if base.exists() else []:
        try:
            meta, corpo = ler_nota(arq)
        except (ValueError, OSError) as erro:
            print(f"aviso: pulei {arq.relative_to(RAIZ)} ({erro})", file=sys.stderr)
            continue
        if not meta.get("id"):
            print(f"aviso: pulei {arq.relative_to(RAIZ)} (frontmatter sem id)", file=sys.stderr)
            continue
        padrao = {**dict.fromkeys(CAMPOS), "status": "bruto", "temas": [], "publicado_em": "", "ingerido_em": "", "titulo": "", "canal": arq.parent.name}
        achadas.append({**padrao, **{k: v for k, v in meta.items() if v is not None}, "_arquivo": arq, "_corpo": corpo})
    return achadas


def secao(corpo, titulo):
    achado = re.search(rf"^## {re.escape(titulo)}[ \t]*\n(.*?)(?=^## |\Z)", corpo, re.S | re.M)
    return achado.group(1).strip() if achado else ""


def relogio(seg):
    seg = int(seg)
    h, m, s = seg // 3600, seg % 3600 // 60, seg % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def montar_nota(canal, video):
    meta = {"id": video["id"], "titulo": video["titulo"], "canal": canal["id"], "canal_nome": canal["nome"],
            "url": f"https://www.youtube.com/watch?v={video['id']}", "publicado_em": video["publicado_em"], "ingerido_em": hoje(),
            "duracao_seg": video["duracao_seg"], "idioma": video["idioma"], "legenda": video["legenda"],
            "visualizacoes": video.get("visualizacoes"), "transcricao_sha": None, "status": "bruto", "relevancia": None, "temas": [], "destilado_em": None}
    linhas = ["---", *(f"{k}: {json.dumps(meta[k], ensure_ascii=False)}" for k in CAMPOS), "---", "", f"# {video['titulo']}", "",
              f"> {canal['nome']} · {video['publicado_em']} · {relogio(video['duracao_seg'])} · {meta['url']}", ""]
    for titulo in SECOES_DESTILADAS:
        linhas += [f"## {titulo}", "", PENDENTE, ""]
    if video.get("capitulos"):
        linhas += ["## Capítulos", "", *(f"- [{relogio(seg)}] {nome}" for seg, nome in video["capitulos"]), ""]
    if video.get("descricao"):
        # "#" no começo de linha da descrição viraria título e confundiria `secao()`
        linhas += ["## Descrição do vídeo", "", re.sub(r"^#", r"\\#", video["descricao"], flags=re.M), ""]
    transcricao = "\n".join(f"[{relogio(seg)}] {texto}\n" for seg, texto in video["blocos"])
    meta["transcricao_sha"] = sha(transcricao)  # o `validar` usa para garantir que ninguém mexeu na transcrição
    linhas[1:1 + len(CAMPOS)] = [f"{k}: {json.dumps(meta[k], ensure_ascii=False)}" for k in CAMPOS]
    return "\n".join([*linhas, "## Transcrição", "", transcricao]).rstrip() + "\n"


def gravar_nota(canal, video):
    pasta = VIDEOS / canal["id"]
    pasta.mkdir(parents=True, exist_ok=True)
    arq = pasta / f"{video['publicado_em']}-{video['id']}-{slug(video['titulo'], 50) or 'video'}.md"
    arq.write_text(montar_nota(canal, video), encoding="utf-8")
    return arq


# ---------- YouTube (tudo o que toca a rede fica aqui) ----------

def _ydl(**opcoes):
    try:
        import yt_dlp
    except ImportError:
        raise SystemExit("falta o yt-dlp: python3 -m pip install -U yt-dlp")
    return yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True, "logger": _Mudo(), **opcoes})


class _Mudo:
    """O yt-dlp escreve cada erro no stderr mesmo em modo quieto; aqui o erro já vira exceção tratada."""
    debug = warning = error = staticmethod(lambda *_: None)


def url_do_canal(url):
    return re.sub(r"/(videos|shorts|streams|featured|playlists|community|about)/?$", "", url.strip().rstrip("/"))


def listar_canal(url, abas=("videos",), limite=None, idioma=None):
    """Vídeos do canal, do mais novo para o mais antigo. A listagem rasa não traz data: ela vem em `baixar_video`.

    Sem `idioma`, o YouTube entrega os títulos da listagem traduzidos por máquina para o inglês (o título da nota não
    sofre disso: ele vem da extração do vídeo, que é sempre o original)."""
    extra = {"extractor_args": {"youtube": {"lang": [idioma]}}} if idioma else {}
    nome = channel_id = None
    videos, vistos = [], set()
    for aba in abas:
        for tentativa in range(TENTATIVAS_LISTAGEM):
            try:
                with _ydl(extract_flat=True, playlistend=limite, **extra) as y:
                    info = y.extract_info(f"{url_do_canal(url)}/{ABAS[aba]}", download=False)
                break
            except Exception as erro:
                if "does not have a" in str(erro):  # canal sem essa aba
                    info = None
                    break
                if BLOQUEIO.search(str(erro)):
                    raise LimiteDeTaxa(str(erro).replace("ERROR: ", "")[:200]) from erro
                if tentativa == TENTATIVAS_LISTAGEM - 1:  # o YouTube falha à toa de vez em quando: só desiste depois de insistir
                    raise Passageiro(str(erro).replace("ERROR: ", "")[:200]) from erro
                time.sleep(3 * (tentativa + 1))
        if info is None:
            continue
        nome, channel_id = nome or info.get("channel") or info.get("uploader"), channel_id or info.get("channel_id")
        for e in info.get("entries") or []:
            if e and e.get("id") and e["id"] not in vistos:
                vistos.add(e["id"])
                videos.append({"id": e["id"], "titulo": e.get("title") or "", "duracao_seg": int(e.get("duration") or 0), "aba": aba})
    if nome is None:
        raise Indisponivel(f"{url}: nenhuma das abas pedidas ({', '.join(abas)}) existe nesse canal")
    return {"nome": nome, "channel_id": channel_id, "videos": videos}


def escolher_legenda(info, idioma_do_canal=None):
    """Legenda escrita pelo canal no idioma do vídeo; senão a automática original (`-orig`), nunca a traduzida por máquina."""
    manuais, automaticas = info.get("subtitles") or {}, info.get("automatic_captions") or {}
    originais = [k for k in automaticas if k.endswith("-orig")]
    idioma = info.get("language") or (originais[0][:-5] if len(originais) == 1 else None) or idioma_do_canal or "en"
    base = idioma.split("-")[0]
    for chave in (idioma, base, *sorted(k for k in manuais if k.split("-")[0] == base)):
        if chave in manuais and chave != "live_chat":
            return manuais[chave], "manual", base
    if originais:  # havendo `-orig`, toda faixa sem o sufixo é tradução de máquina, inclusive a do idioma que o YouTube declarou
        do_idioma = [k for k in originais if k.split("-")[0] == base]
        chave = do_idioma[0] if do_idioma else originais[0] if len(originais) == 1 else None
        if chave:
            return automaticas[chave], "automatica", chave[:-5].split("-")[0]
    else:
        for chave in (idioma, base):
            if chave in automaticas:
                return automaticas[chave], "automatica", base
    raise SemLegenda("vídeo sem legenda no idioma original")


def blocos_da_legenda(eventos, minimo=45, maximo=90):
    """json3 do YouTube -> parágrafos de ~1 min com o segundo em que começam."""
    blocos, atual, inicio = [], [], None
    for ev in eventos:
        texto = "".join(s.get("utf8", "") for s in ev.get("segs") or [])
        texto = re.sub(r"\[(music|música|applause|aplausos|laughter|risos)\]", " ", texto, flags=re.I)
        texto = " ".join(texto.split())
        if not texto:
            continue
        seg = (ev.get("tStartMs") or 0) / 1000
        if inicio is None:
            inicio = seg
        atual.append(texto)
        passou = seg - inicio
        if passou >= maximo or (passou >= minimo and texto[-1] in ".?!"):
            blocos.append((int(inicio), " ".join(atual)))
            atual, inicio = [], None
    if atual:
        blocos.append((int(inicio), " ".join(atual)))
    return blocos


def data_iso(info):
    d = info.get("upload_date") or ""
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}" if len(d) == 8 else None


def baixar_video(video_id, idioma_do_canal=None):
    try:
        with _ydl() as y:
            info = y.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    except Exception as erro:
        motivo = str(erro).replace("ERROR: ", "").replace(video_id, "<id>")[:200]  # o id pode conter "429" por acaso
        tipo = LimiteDeTaxa if BLOQUEIO.search(motivo) else Indisponivel if PERMANENTE.search(motivo) else Passageiro
        raise tipo(motivo) from erro
    if not data_iso(info):
        raise Passageiro("o YouTube ainda não informa a data de publicação (estreia ou live agendada)")
    try:
        formatos, tipo, idioma = escolher_legenda(info, idioma_do_canal)
    except SemLegenda as erro:
        raise SemLegenda(str(erro), data_iso(info)) from None
    json3 = next((f["url"] for f in formatos if f.get("ext") == "json3"), None)
    if not json3:
        raise SemLegenda("legenda sem formato json3", data_iso(info))
    try:
        with urllib.request.urlopen(urllib.request.Request(json3, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as resposta:
            eventos = json.loads(resposta.read()).get("events") or []
    except Exception as erro:
        raise (LimiteDeTaxa if getattr(erro, "code", None) == 429 else Passageiro)(f"falha ao baixar a legenda: {erro}"[:200]) from erro
    blocos = blocos_da_legenda(eventos)
    if not blocos:
        raise SemLegenda("legenda vazia", data_iso(info))
    return {"id": video_id, "titulo": info.get("title") or "", "publicado_em": data_iso(info),
            "duracao_seg": int(info.get("duration") or 0), "idioma": idioma, "legenda": tipo, "visualizacoes": info.get("view_count"),
            "descricao": (info.get("description") or "").strip()[:1500],
            "capitulos": [(c.get("start_time") or 0, c.get("title") or "") for c in info.get("chapters") or []], "blocos": blocos}


# ---------- ingestão ----------

def ingerir(canal, candidatos, limite=None, pausa=4.0, log=print):
    """Baixa e grava o que ainda não está no disco, gravando o estado a cada vídeo. Devolve o resumo da rodada.

    Destino de quem falha: erro definitivo ou vídeo antigo sem legenda -> `descartados` (não volta sozinho);
    vídeo recente sem legenda ou erro passageiro -> `aguardando` (volta nas próximas rodadas);
    bloqueio do YouTube ou falhas de rede em sequência -> a rodada para e nada é marcado."""
    cid, desde = canal["id"], canal.get("desde")
    est = estado_do_canal(carregar_estado(), cid)
    no_disco = {n["id"] for n in notas(cid)}
    feito = {"novos": [], "aguardando": [], "descartados": [], "interrompido": None, "restam": 0}
    fila = [v for v in candidatos if v["id"] not in no_disco and v["id"] not in est["descartados"]]
    abas_encerradas = set()  # cada aba vem do mais novo para o mais antigo: passou do corte, o resto dela é anterior
    seguidas = recuos = 0

    def faltam(n):
        return sum(1 for r in fila[n:] if r.get("aba") not in abas_encerradas)

    for n, v in enumerate(fila):
        if v.get("aba") in abas_encerradas:
            continue
        if limite is not None and len(feito["novos"]) >= limite:
            feito["restam"] = faltam(n)
            break
        if n:
            time.sleep(pausa * random.uniform(0.7, 1.6))  # ritmo de máquina é o que dispara o bloqueio
        try:
            while True:
                try:
                    video = baixar_video(v["id"], canal.get("idioma"))
                    break
                except LimiteDeTaxa:
                    if recuos >= len(RECUOS):
                        raise
                    log(f"  ~ o YouTube bloqueou; espero {RECUOS[recuos]} s e insisto ({recuos + 1}/{len(RECUOS)})")
                    time.sleep(RECUOS[recuos])
                    recuos += 1
            seguidas = 0
        except LimiteDeTaxa as erro:
            feito["interrompido"], feito["restam"] = f"o YouTube bloqueou as requisições mesmo depois de {len(RECUOS)} esperas. Rode de novo mais tarde. ({erro})"[:240], faltam(n)
            break
        except (SemLegenda, Indisponivel, Passageiro) as erro:
            espera = est["aguardando"].get(v["id"], {"titulo": v["titulo"], "desde": hoje(), "tentativas": 0})
            espera.update(tentativas=espera["tentativas"] + 1, motivo=str(erro))
            if isinstance(erro, Passageiro):
                seguidas += 1
                volta = True  # passageiro nunca descarta, por mais que demore
            else:
                seguidas = 0
                # sem legenda: só quem acabou de sair merece espera, porque a automática demora umas horas
                nasceu = getattr(erro, "publicado_em", None) or (espera["desde"] if v.get("recente") else None)
                volta = (isinstance(erro, SemLegenda) and nasceu is not None and espera["tentativas"] < MAX_TENTATIVAS
                         and (date.today() - date.fromisoformat(nasceu)).days <= ESPERA_LEGENDA_DIAS)
            if volta:
                est["aguardando"][v["id"]] = espera
                feito["aguardando"].append({"id": v["id"], "titulo": v["titulo"], "motivo": str(erro)})
            else:
                est["aguardando"].pop(v["id"], None)
                est["descartados"][v["id"]] = {"titulo": v["titulo"], "motivo": str(erro), "em": hoje()}
                feito["descartados"].append({"id": v["id"], "titulo": v["titulo"], "motivo": str(erro)})
            salvar_estado_do_canal(cid, est)
            log(f"  - {v['id']} {v['titulo'][:60]}: {erro}")
            if seguidas >= FALHAS_SEGUIDAS:
                feito["interrompido"], feito["restam"] = f"{seguidas} falhas de rede seguidas: parei para não marcar vídeo bom como problema. ({erro})"[:240], faltam(n + 1)
                break
            continue
        if desde and video["publicado_em"] < desde:
            abas_encerradas.add(v.get("aba"))
            est["aguardando"].pop(v["id"], None)
            est["descartados"][v["id"]] = {"titulo": video["titulo"], "motivo": f"{CORTE} {desde}", "em": hoje()}
            salvar_estado_do_canal(cid, est)
            log(f"  · {video['publicado_em']} é anterior a {desde}: encerrei a aba '{v.get('aba')}'.")
            continue
        arq = gravar_nota(canal, video)
        est["aguardando"].pop(v["id"], None)
        ultimo = est.get("ultimo_video")
        if not ultimo or video["publicado_em"] >= ultimo["publicado_em"]:
            est["ultimo_video"] = {"id": video["id"], "titulo": video["titulo"], "publicado_em": video["publicado_em"]}
        salvar_estado_do_canal(cid, est)
        feito["novos"].append({"id": video["id"], "titulo": video["titulo"], "publicado_em": video["publicado_em"], "arquivo": str(arq.relative_to(RAIZ))})
        log(f"  + {video['publicado_em']} {video['titulo'][:70]}")
    est["ultima_varredura"] = datetime.now().astimezone().isoformat(timespec="seconds")
    salvar_estado_do_canal(cid, est)
    return feito


def cmd_canal_add(args):
    canais, url = carregar_canais(), url_do_canal(args.url)
    abas = ["videos"] + (["shorts"] if args.shorts else []) + (["lives"] if args.lives else [])
    info = listar_canal(url, abas, limite=5, idioma=args.idioma)
    handle = re.search(r"@([^/]+)", url)
    cid = args.id or slug(info["nome"], 40) or slug(handle.group(1) if handle else "", 40) or slug(info["channel_id"] or "", 40)
    if not cid:
        raise SystemExit("não consegui derivar um apelido do nome do canal: passe --id <apelido>.")
    for c in canais:
        if c["id"] == cid or (info["channel_id"] and c.get("channel_id") == info["channel_id"]):
            raise SystemExit(f"esse canal já está cadastrado como '{c['id']}'.")
    canal = {"id": cid, "nome": info["nome"], "url": url, "channel_id": info["channel_id"], "abas": abas, "ativo": True,
             "idioma": args.idioma, "desde": args.desde, "adicionado_em": hoje(), "nota": args.nota or ""}
    if not args.previa:
        salvar_canais(canais + [canal])
    return {"canal": canal, "previa": args.previa, "amostra": [v["titulo"] for v in info["videos"]]}


# ---------- descoberta: achar canal novo pelo que está bombando na busca do YouTube ----------
JANELAS_DA_BUSCA = {"mes": "CAMSAggE", "ano": "CAMSAggF"}   # filtro `sp` do YouTube: enviado neste mês / neste ano, ordenado por visualizações
DESCOBERTA_PADRAO = {"janelas": ["mes", "ano"], "resultados_por_busca": 15, "duracao_minima_seg": 180, "minimo_visualizacoes": 100_000,
                     "minimo_inscritos": 100_000, "max_candidatos": 10, "max_canais_por_rodada": 3, "titulos_por_canal": 30, "corte_meses": 12,
                     "importar_por_rodada": 40, "reavaliar_recusado_apos_dias": 60, "fatia_minima": 0.5, "palavras_do_tema": []}


def descoberta_config():
    arq = PASTA / "descoberta.json"
    if not arq.exists():
        raise SystemExit(f"{BASE['nome']} não tem descoberta configurada: falta {arq.relative_to(RAIZ)} (consultas e critérios).")
    cfg = {**DESCOBERTA_PADRAO, **{k: v for k, v in ler_json(arq, {}).items() if not k.startswith("_")}}
    if not cfg.get("consultas"):
        raise SystemExit(f"{arq.relative_to(RAIZ)} não tem nenhuma consulta.")
    return cfg


def descoberta_estado_arq():
    return ESTADO.with_name(f"{BASE['id']}-descoberta.json")


def buscar_no_youtube(consulta, janela, limite, idioma=None):
    """Resultados da busca, já ordenados por visualizações dentro da janela. Listagem rasa: uma requisição."""
    import urllib.parse
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(consulta)}&sp={JANELAS_DA_BUSCA[janela]}"
    extra = {"extractor_args": {"youtube": {"lang": [idioma]}}} if idioma else {}
    try:
        with _ydl(extract_flat=True, playlistend=limite, **extra) as y:
            info = y.extract_info(url, download=False)
    except Exception as erro:
        if BLOQUEIO.search(str(erro)):
            raise LimiteDeTaxa(str(erro).replace("ERROR: ", "")[:200]) from erro
        raise Passageiro(str(erro).replace("ERROR: ", "")[:200]) from erro
    return [{"id": e["id"], "titulo": e.get("title") or "", "visualizacoes": int(e.get("view_count") or 0), "duracao_seg": int(e.get("duration") or 0),
             "canal_nome": e.get("channel") or e.get("uploader") or "", "channel_id": e.get("channel_id")}
            for e in (info.get("entries") or []) if e and e.get("id") and e.get("channel_id")]


def inscritos_do_canal(video_id):
    """O número de inscritos só vem na extração de um vídeo do canal (a listagem do canal não traz)."""
    try:
        with _ydl() as y:
            info = y.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False, process=False)
    except Exception as erro:
        if BLOQUEIO.search(str(erro)):
            raise LimiteDeTaxa(str(erro).replace("ERROR: ", "")[:200]) from erro
        raise Passageiro(str(erro).replace("ERROR: ", "")[:200]) from erro
    return info.get("channel_follower_count"), info.get("language")


def fatia_no_tema(titulos, palavras):
    """Que parte dos títulos bate com as palavras do tema. É só um termômetro: quem decide "a maior parte do canal" lê os títulos."""
    if not titulos or not palavras:
        return None
    padrao = re.compile("|".join(rf"(?<!\w){re.escape(sem_acento(p))}(?!\w)" for p in palavras), re.I)
    return round(sum(1 for tit in titulos if padrao.search(sem_acento(tit))) / len(titulos), 2)


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn").lower()


def cmd_descobrir(args, log, pausa=1.5):
    cfg, canais, hoje_ = descoberta_config(), carregar_canais(), date.today()
    estado = ler_json(descoberta_estado_arq(), {"avaliados": {}, "candidatos": {}})
    cadastrados = {c.get("channel_id") for c in canais}
    validade = cfg["reavaliar_recusado_apos_dias"]
    vistos = {cid for cid, a in estado["avaliados"].items() if a["veredito"] == "aprovado" or (hoje_ - date.fromisoformat(a["quando"])).days < validade}
    por_canal, buscas, interrompido = {}, 0, None
    try:
        for c in cfg["consultas"]:
            consulta, idioma = (c, None) if isinstance(c, str) else (c["q"], c.get("idioma"))
            for janela in cfg["janelas"]:
                for v in buscar_no_youtube(consulta, janela, cfg["resultados_por_busca"], idioma):
                    if v["duracao_seg"] and v["duracao_seg"] < cfg["duracao_minima_seg"]:
                        continue   # short viral não diz nada sobre o canal
                    k = por_canal.setdefault(v["channel_id"], {"channel_id": v["channel_id"], "nome": v["canal_nome"], "idioma": idioma, "videos": {}, "consultas": set()})
                    k["videos"][v["id"]] = v
                    k["consultas"].add(consulta)
                buscas += 1
                log(f"  busca {buscas}: '{consulta}' ({janela}) · {len(por_canal)} canais até aqui")
                time.sleep(pausa * random.uniform(0.7, 1.4))
        novos = sorted((k for cid, k in por_canal.items() if cid not in cadastrados and cid not in vistos),
                       # canal que aparece em várias buscas e com vários vídeos é canal do assunto; vídeo único de portal gigante vem depois
                       key=lambda k: (-len(k["consultas"]), -len(k["videos"]), -max(v["visualizacoes"] for v in k["videos"].values())))
        candidatos = []
        for k in novos[:cfg["max_candidatos"]]:
            topo = max(k["videos"].values(), key=lambda v: v["visualizacoes"])
            inscritos, idioma_do_video = inscritos_do_canal(topo["id"])
            time.sleep(pausa * random.uniform(0.7, 1.4))
            por_video, por_inscritos = topo["visualizacoes"] >= cfg["minimo_visualizacoes"], (inscritos or 0) >= cfg["minimo_inscritos"]
            if not (por_video or por_inscritos):
                estado["avaliados"][k["channel_id"]] = {"quando": hoje_.isoformat(), "nome": k["nome"], "veredito": "recusado", "por": "script",
                                                        "motivo": f"abaixo do corte: vídeo com {topo['visualizacoes']} visualizações e canal com {inscritos} inscritos"}
                continue
            lista = listar_canal(f"https://www.youtube.com/channel/{k['channel_id']}", ("videos",), limite=cfg["titulos_por_canal"], idioma=k["idioma"])
            time.sleep(pausa * random.uniform(0.7, 1.4))
            titulos = [v["titulo"] for v in lista["videos"]]
            candidatos.append({"channel_id": k["channel_id"], "nome": lista["nome"] or k["nome"], "url": f"https://www.youtube.com/channel/{k['channel_id']}",
                               "inscritos": inscritos, "idioma": idioma_do_video or k["idioma"], "passou_por": [n for n, ok in (("video", por_video), ("inscritos", por_inscritos)) if ok],
                               "video_gatilho": {kk: topo[kk] for kk in ("id", "titulo", "visualizacoes")}, "achado_em": sorted(k["consultas"]),
                               "videos_achados": len(k["videos"]), "titulos": titulos, "fatia_por_palavras": fatia_no_tema(titulos, cfg["palavras_do_tema"])})
    except LimiteDeTaxa as erro:
        interrompido, candidatos = f"bloqueio do YouTube: {erro}", locals().get("candidatos", [])
    except Passageiro as erro:
        interrompido, candidatos = f"erro passageiro: {erro}", locals().get("candidatos", [])
    estado["candidatos"] = {c["channel_id"]: {**{k: c[k] for k in ("nome", "url", "inscritos", "passou_por", "video_gatilho", "fatia_por_palavras")}, "quando": hoje_.isoformat()} for c in candidatos}
    gravar_json(descoberta_estado_arq(), estado)
    meses = hoje_.year * 12 + hoje_.month - 1 - cfg["corte_meses"]   # o corte de data do canal novo: N meses para trás
    corte = date(meses // 12, meses % 12 + 1, min(hoje_.day, 28)) if cfg["corte_meses"] else None
    return {"temas_alvo": cfg.get("temas_alvo"), "criterio": f"vídeo com {cfg['minimo_visualizacoes']} visualizações ou canal com {cfg['minimo_inscritos']} inscritos, e mais de "
            f"{int(cfg['fatia_minima'] * 100)}% dos títulos recentes no tema", "buscas": buscas, "canais_vistos": len(por_canal), "ja_cadastrados": len(cadastrados & set(por_canal)),
            "candidatos": candidatos, "max_canais_por_rodada": cfg["max_canais_por_rodada"], "importar_por_rodada": cfg["importar_por_rodada"],
            "desde_sugerido": corte.isoformat() if corte else None, "fatia_minima": cfg["fatia_minima"], "interrompido": interrompido}


def cmd_descobrir_veredito(args):
    """O julgamento de quem leu os títulos fica registrado: aprovado não volta a ser candidato; recusado volta depois da validade."""
    estado = ler_json(descoberta_estado_arq(), {"avaliados": {}, "candidatos": {}})
    cand = estado["candidatos"].get(args.channel_id)
    if not cand:
        raise SystemExit(f"{args.channel_id} não está entre os candidatos da última busca. Rode `python3 {BASE['id']}.py descobrir` antes.")
    if args.veredito == "aprovado" and not cand["passou_por"]:
        raise SystemExit("esse canal não passou no corte de visualizações nem de inscritos: não pode ser aprovado.")
    if args.veredito == "aprovado" and not (0 <= args.no_tema <= args.lidos and args.lidos > 0 and args.no_tema / args.lidos > descoberta_config()["fatia_minima"]):
        raise SystemExit(f"{args.no_tema} de {args.lidos} títulos no tema não é a maior parte do canal: o veredito tem que ser recusado.")
    estado["avaliados"][args.channel_id] = {"quando": date.today().isoformat(), "nome": cand["nome"], "url": cand["url"], "veredito": args.veredito, "por": "agente",
                                            "motivo": args.motivo, "no_tema": args.no_tema, "lidos": args.lidos, "inscritos": cand["inscritos"],
                                            "video_gatilho": cand["video_gatilho"]}
    gravar_json(descoberta_estado_arq(), estado)
    return {"channel_id": args.channel_id, **estado["avaliados"][args.channel_id]}


def cmd_canal_remover(args):
    canais = carregar_canais()
    canal = achar_canal(canais, args.canal)
    if notas(canal["id"]):
        raise SystemExit(f"'{canal['id']}' já tem notas {BASE['onde']}. Para parar de acompanhar, use `canal pausar {canal['id']}`.")
    salvar_canais([c for c in canais if c is not canal])
    estado = carregar_estado()
    if estado["canais"].pop(canal["id"], None) is not None:
        gravar_json(ESTADO, estado)
    return {"canal": canal["id"], "removido": True}


def cmd_canal_ativo(args, ativo):
    canais = carregar_canais()
    achar_canal(canais, args.canal)["ativo"] = ativo
    salvar_canais(canais)
    return {"canal": args.canal, "ativo": ativo}


def cmd_importar(args, log):
    canais = carregar_canais()
    canal = achar_canal(canais, args.canal)
    if args.video:  # um vídeo só, inclusive um que tinha sido descartado
        est = estado_do_canal(carregar_estado(), canal["id"])
        est["descartados"].pop(args.video, None)
        salvar_estado_do_canal(canal["id"], est)
        return {canal["id"]: {"no_canal": None, **ingerir({**canal, "desde": None}, [{"id": args.video, "titulo": args.video}], None, 0, log)}}
    if args.desde and args.desde != canal.get("desde"):
        # o corte mora no canal: é ele que impede o `varrer` de trazer o acervo antigo depois
        canal["desde"] = None if args.desde == "tudo" else args.desde
        salvar_canais(canais)
        est = estado_do_canal(carregar_estado(), canal["id"])
        est["descartados"] = {k: v for k, v in est["descartados"].items() if not v.get("motivo", "").startswith(CORTE)}
        salvar_estado_do_canal(canal["id"], est)
    log(f"{canal['nome']}: listando o canal inteiro..." + (f" (corte: {canal['desde']})" if canal.get("desde") else ""))
    videos = listar_canal(canal["url"], canal.get("abas") or ["videos"], idioma=canal.get("idioma"))["videos"]
    log(f"{len(videos)} vídeos no canal.")
    return {canal["id"]: {"no_canal": len(videos), **ingerir(canal, videos, args.limite, args.pausa, log)}}


def cmd_varrer(args, log):
    canais, saida = carregar_canais(), {}
    alvo = [achar_canal(canais, args.canal)] if args.canal else [c for c in canais if c.get("ativo", True)]
    for canal in alvo:
        log(f"{canal['nome']}:")
        try:
            videos = listar_canal(canal["url"], canal.get("abas") or ["videos"], limite=args.ultimos, idioma=canal.get("idioma"))["videos"]
        except (Indisponivel, Passageiro, LimiteDeTaxa) as erro:
            saida[canal["id"]] = {"erro": str(erro)}
            log(f"  ! {erro}")
            if isinstance(erro, LimiteDeTaxa):
                break
            continue
        for v in videos:
            v["recente"] = True
        # quem ficou esperando volta para a fila mesmo que já tenha saído dos últimos N do canal
        listados = {v["id"] for v in videos}
        espera = estado_do_canal(carregar_estado(), canal["id"])["aguardando"]
        videos += [{"id": vid, "titulo": e.get("titulo", vid), "recente": True, "aba": f"espera:{vid}"} for vid, e in espera.items() if vid not in listados]
        no_disco = {n["id"] for n in notas(canal["id"])}
        feito = ingerir(canal, videos, args.limite, args.pausa, log)
        if listados and not no_disco & listados and not canal.get("desde"):
            feito["aviso"] = (f"nenhum dos últimos {len(listados)} vídeos estava {BASE['onde']}: pode haver acervo para trás. "
                              f"Rode `python3 {BASE['id']}.py importar {canal['id']}`.")
        saida[canal["id"]] = feito
        if feito["interrompido"]:
            break
    return saida


def resumo_dos_canais():
    estado, linhas = carregar_estado(), []
    for c in carregar_canais():
        do_canal, est = notas(c["id"]), estado["canais"].get(c["id"], {})
        linhas.append({"id": c["id"], "nome": c["nome"], "url": c["url"], "ativo": c.get("ativo", True), "notas": len(do_canal),
                       "destiladas": sum(n["status"] == "destilado" for n in do_canal), "ultimo_video": est.get("ultimo_video"),
                       "ultima_varredura": est.get("ultima_varredura"), "aguardando": len(est.get("aguardando", {})),
                       "descartados": len(est.get("descartados", {}))})
    return linhas


def cmd_pendentes(args):
    brutas = sorted((n for n in notas(args.canal) if n["status"] != "destilado"), key=lambda n: n["publicado_em"], reverse=True)
    return {"total": len(brutas), "notas": [{"id": n["id"], "titulo": n["titulo"], "canal": n["canal"], "publicado_em": n["publicado_em"],
                                             "arquivo": str(n["_arquivo"].relative_to(RAIZ))} for n in brutas[:args.limite]]}


def uteis():
    return [n for n in notas() if n["status"] == "destilado" and n.get("relevancia") != "fora"]


def cmd_buscar(args):
    achadas = []
    for n in sorted(uteis(), key=lambda n: n["publicado_em"], reverse=True):
        if args.tema and args.tema not in n["temas"]:
            continue
        if args.canal and n["canal"] != args.canal:
            continue
        if args.desde and n["publicado_em"] < args.desde:
            continue
        if args.texto and args.texto.lower() not in (n["titulo"] + secao(n["_corpo"], "Resumo") + secao(n["_corpo"], BASE["secao_itens"])).lower():
            continue
        item = {k: n[k] for k in ("id", "titulo", "canal", "publicado_em", "relevancia", "temas", "url")}
        item.update(arquivo=str(n["_arquivo"].relative_to(RAIZ)), resumo=secao(n["_corpo"], "Resumo"))
        if args.itens:
            item.update({BASE["itens"]: secao(n["_corpo"], BASE["secao_itens"]), "ressalvas": secao(n["_corpo"], "Ressalvas")})
        achadas.append(item)
    return achadas[:args.limite]


def cmd_indice():
    todas, boas = notas(), uteis()
    rotulos = {t["id"]: t["nome"] for t in ler_json(TEMAS, {"temas": []})["temas"]}
    linhas = [f"# {BASE['titulo']}: índice", "", f"Gerado por `python3 {BASE['id']}.py indice`. Não edite à mão.", "",
              f"{len(todas)} notas, {len(boas)} destiladas e úteis. Consulta por tema: `python3 {BASE['id']}.py buscar --tema <tema> --{BASE['itens']}`.", "",
              "## Canais", "", "| Canal | Notas | Destiladas | Último vídeo |", "|---|---|---|---|"]
    for c in resumo_dos_canais():
        ultimo = c["ultimo_video"]
        linhas.append(f"| [{c['nome']}]({c['url']}){'' if c['ativo'] else ' (pausado)'} | {c['notas']} | {c['destiladas']} | "
                      f"{ultimo['publicado_em'] + ' · ' + ultimo['titulo'] if ultimo else 'nada ainda'} |")
    ordem = {"alta": 0, "media": 1, "baixa": 2}
    for tema, nome in rotulos.items():
        do_tema = sorted((n for n in boas if tema in n["temas"]), key=lambda n: n["publicado_em"], reverse=True)
        do_tema.sort(key=lambda n: ordem.get(n.get("relevancia"), 3))
        if do_tema:
            linhas += ["", f"## {nome} (`{tema}`)", ""]
            linhas += [f"- {n['publicado_em']} · [{n['titulo']}]({n['_arquivo'].relative_to(PASTA).as_posix()}) · {n['canal_nome']} · {n['relevancia']}"
                       for n in do_tema]
    INDICE.parent.mkdir(parents=True, exist_ok=True)
    INDICE.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return {"arquivo": str(INDICE.relative_to(RAIZ)), "notas": len(todas), "uteis": len(boas)}


def cmd_validar():
    erros, validos, ids = [], set(temas_validos()), {}
    canais = {c["id"] for c in carregar_canais()}
    for arq in sorted(VIDEOS.rglob("*.md")) if VIDEOS.exists() else []:
        rel = str(arq.relative_to(RAIZ))
        try:
            meta, corpo = ler_nota(arq)
        except (ValueError, OSError) as erro:
            erros.append(f"{rel}: {erro}")
            continue
        faltam = [k for k in CAMPOS if k not in meta and k != "transcricao_sha"]
        if faltam:
            erros.append(f"{rel}: faltam campos no frontmatter: {', '.join(faltam)}")
            continue
        if meta["id"] in ids:
            erros.append(f"{rel}: vídeo {meta['id']} duplicado (também em {ids[meta['id']]})")
        ids[meta["id"]] = rel
        if meta["canal"] not in canais:
            erros.append(f"{rel}: canal '{meta['canal']}' não está em {BASE['id']}/canais.json")
        if not secao(corpo, "Transcrição"):
            erros.append(f"{rel}: sem transcrição")
        elif meta.get("transcricao_sha") and sha(secao(corpo, "Transcrição")) != meta["transcricao_sha"]:
            erros.append(f"{rel}: a Transcrição foi alterada depois da ingestão (reimporte com `importar {meta['canal']} --video {meta['id']}` após apagar a nota)")
        if meta["status"] == "bruto":
            continue
        if meta["status"] != "destilado":
            erros.append(f"{rel}: status '{meta['status']}' não existe (bruto ou destilado)")
        if meta["relevancia"] not in RELEVANCIAS:
            erros.append(f"{rel}: relevancia '{meta['relevancia']}' não existe ({', '.join(RELEVANCIAS)})")
        if not meta["destilado_em"]:
            erros.append(f"{rel}: destilado sem `destilado_em`")
        if meta.get("_temas_fora_do_formato"):
            erros.append(f"{rel}: a linha `temas` não está no JSON que o script grava. Escreva: "
                         f"temas: {json.dumps(meta['temas'], ensure_ascii=False)}")
        fora = [t for t in meta["temas"] if t not in validos]
        if fora:
            erros.append(f"{rel}: tema fora de {BASE['id']}/temas.json: {', '.join(fora)}")
        if meta["relevancia"] != "fora":
            if not meta["temas"]:
                erros.append(f"{rel}: destilado sem tema")
            # a busca por tema lê o frontmatter: tema marcado só no item ficaria invisível
            marcados = set(re.findall(r"\[([a-z][a-z-]+)\]", secao(corpo, BASE["secao_itens"])))
            if marcados - validos:
                erros.append(f"{rel}: tema fora de {BASE['id']}/temas.json marcado em {BASE['item']}: {', '.join(sorted(marcados - validos))}")
            if marcados & validos - set(meta["temas"]):
                erros.append(f"{rel}: tema usado em {BASE['item']} e ausente do frontmatter: {', '.join(sorted(marcados & validos - set(meta['temas'])))}")
            for titulo in SECOES_DESTILADAS:
                if not secao(corpo, titulo) or PENDENTE in secao(corpo, titulo):
                    erros.append(f"{rel}: seção '{titulo}' não foi escrita")
        elif not secao(corpo, "Resumo") or PENDENTE in secao(corpo, "Resumo"):
            erros.append(f"{rel}: nota `fora` precisa dizer no Resumo por que ficou de fora")
    return {"ok": not erros, "notas": len(ids), "erros": erros}


# ---------- CLI ----------

def main(argv=None):
    p = argparse.ArgumentParser(description=BASE["descricao"], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    canal = sub.add_parser("canal").add_subparsers(dest="acao", required=True)
    add = canal.add_parser("add")
    add.add_argument("url")
    add.add_argument("--id", help="apelido curto do canal (padrão: o nome do canal em slug)")
    add.add_argument("--nota", help="por que esse canal está aqui")
    add.add_argument("--idioma", help="idioma do canal (pt, en...), usado só quando o YouTube não informa o do vídeo")
    add.add_argument("--desde", help=f"AAAA-MM-DD: {BASE['nome']} ignora o que esse canal publicou antes (vale para importar e varrer)")
    add.add_argument("--previa", action="store_true", help="só mostra o nome e os últimos títulos do canal, sem cadastrar")
    add.add_argument("--shorts", action="store_true", help="também acompanhar a aba de Shorts")
    add.add_argument("--lives", action="store_true", help="também acompanhar a aba Ao vivo")
    for acao in ("pausar", "ativar", "remover"):
        canal.add_parser(acao).add_argument("canal")
    sub.add_parser("canais")
    imp = sub.add_parser("importar")
    imp.add_argument("canal")
    imp.add_argument("--desde", help="AAAA-MM-DD: grava o corte no canal e ignora o que foi publicado antes; `tudo` remove o corte")
    imp.add_argument("--video", help="id de um vídeo só: ingere (ou tenta de novo) esse vídeo")
    var = sub.add_parser("varrer")
    var.add_argument("canal", nargs="?")
    var.add_argument("--ultimos", type=int, default=30, help="quantos vídeos recentes olhar em cada canal")
    for x in (imp, var):
        x.add_argument("--limite", type=int, help="no máximo N vídeos novos nesta rodada (por canal)")
        x.add_argument("--pausa", type=float, default=4.0, help="segundos entre um vídeo e outro, em média (o intervalo real varia)")
    pen = sub.add_parser("pendentes")
    pen.add_argument("--canal")
    pen.add_argument("--limite", type=int, default=20)
    bus = sub.add_parser("buscar")
    bus.add_argument("--tema")
    bus.add_argument("--texto")
    bus.add_argument("--canal")
    bus.add_argument("--desde")
    bus.add_argument(f"--{BASE['itens']}", dest="itens", action="store_true", help=f"traz as seções {BASE['secao_itens']} e Ressalvas de cada nota")
    bus.add_argument("--limite", type=int, default=20)
    for nome in ("indice", "validar", "status"):
        sub.add_parser(nome)
    sub.add_parser("descobrir", help="busca no YouTube o que está bombando nos temas da base e devolve canais candidatos")
    ver = sub.add_parser("descobrir-veredito", help="registra o julgamento de um candidato da última busca")
    ver.add_argument("channel_id")
    ver.add_argument("veredito", choices=("aprovado", "recusado"))
    ver.add_argument("--no-tema", dest="no_tema", type=int, required=True, help="quantos dos títulos lidos são do tema")
    ver.add_argument("--lidos", type=int, required=True, help="quantos títulos foram lidos")
    ver.add_argument("--motivo", required=True)
    for x in (add, *(canal.choices[a] for a in ("pausar", "ativar", "remover")), *(sub.choices[n] for n in sub.choices if n != "canal")):
        x.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    log = (lambda *_: None) if args.json else print

    if args.cmd == "canal":
        saida = (cmd_canal_add(args) if args.acao == "add" else cmd_canal_remover(args) if args.acao == "remover"
                 else cmd_canal_ativo(args, args.acao == "ativar"))
    elif args.cmd == "importar":
        saida = cmd_importar(args, log)
    elif args.cmd == "varrer":
        saida = cmd_varrer(args, log)
    elif args.cmd == "pendentes":
        saida = cmd_pendentes(args)
    elif args.cmd == "buscar":
        if args.tema and args.tema not in temas_validos():
            raise SystemExit(f"tema '{args.tema}' não existe. Temas: {', '.join(temas_validos())}")
        saida = cmd_buscar(args)
    elif args.cmd == "descobrir":
        saida = cmd_descobrir(args, log)
    elif args.cmd == "descobrir-veredito":
        saida = cmd_descobrir_veredito(args)
    elif args.cmd == "indice":
        saida = cmd_indice()
    elif args.cmd == "validar":
        saida = cmd_validar()
    else:
        canais = resumo_dos_canais()
        saida = {"canais": canais, "notas": sum(c["notas"] for c in canais), "destiladas": sum(c["destiladas"] for c in canais),
                 "pendentes": sum(c["notas"] - c["destiladas"] for c in canais)} if args.cmd == "status" else canais

    if args.json:
        print(json.dumps(saida, ensure_ascii=False, indent=1, default=str))
    else:
        mostrar(args, saida)
    if args.cmd == "validar":
        return 0 if saida["ok"] else 1
    if args.cmd == "descobrir":
        return 2 if saida["interrompido"] else 0
    if args.cmd in ("importar", "varrer"):  # o cron precisa enxergar rodada que não terminou
        return 2 if any("erro" in r or r.get("interrompido") for r in saida.values()) else 0
    return 0


def mostrar(args, saida):
    if args.cmd == "canal" and args.acao == "add":
        c = saida["canal"]
        print(f"{'PRÉVIA, nada foi gravado' if saida['previa'] else 'cadastrado'}: {c['id']} ({c['nome']}, abas: {', '.join(c['abas'])}"
              f"{', corte: ' + c['desde'] if c['desde'] else ''})\nÚltimos vídeos, para conferir se é o canal certo:")
        print("\n".join(f"  · {t}" for t in saida["amostra"]))
        print("Se for o canal certo, rode de novo sem --previa." if saida["previa"] else f"Próximo passo: python3 {BASE['id']}.py importar {c['id']}")
    elif args.cmd == "descobrir":
        print(f"{saida['buscas']} buscas, {saida['canais_vistos']} canais vistos, {saida['ja_cadastrados']} já cadastrados. Critério: {saida['criterio']}.")
        for c in saida["candidatos"]:
            g = c["video_gatilho"]
            print(f"\n{c['nome']}  {c['url']}\n   {c['inscritos'] or '?'} inscritos · passou por: {', '.join(c['passou_por'])} · termômetro por palavra: {c['fatia_por_palavras']}"
                  f"\n   vídeo que chamou a atenção: {g['visualizacoes']} visualizações · {g['titulo']}\n   últimos títulos:")
            print("\n".join(f"     · {tit}" for tit in c["titulos"][:12]))
        print("\nnenhum candidato novo." if not saida["candidatos"] else f"\nLeia os títulos, registre cada veredito com `descobrir-veredito` e cadastre no máximo {saida['max_canais_por_rodada']}.")
        if saida["interrompido"]:
            print(f"RODADA INTERROMPIDA: {saida['interrompido']}")
    elif args.cmd == "descobrir-veredito":
        print(f"{saida['nome']}: {saida['veredito']} ({saida['no_tema']} de {saida['lidos']} títulos no tema). {saida['motivo']}")
    elif args.cmd in ("canais", "status"):
        for c in saida["canais"] if args.cmd == "status" else saida:
            u = c["ultimo_video"]
            print(f"{c['id']}{'' if c['ativo'] else ' (pausado)'}: {c['notas']} notas, {c['destiladas']} destiladas, {c['aguardando']} esperando legenda, "
                  f"{c['descartados']} descartados\n   último vídeo: {u['publicado_em'] + ' · ' + u['titulo'] if u else 'nada ainda'}\n"
                  f"   última varredura: {c['ultima_varredura'] or 'nunca'}")
        if args.cmd == "status":
            print(f"total: {saida['notas']} notas, {saida['destiladas']} destiladas, {saida['pendentes']} por destilar")
    elif args.cmd in ("importar", "varrer"):
        for cid, r in saida.items():
            if "erro" in r:
                print(f"{cid}: ERRO {r['erro']}")
                continue
            print(f"{cid}: {len(r['novos'])} novos, {len(r['aguardando'])} esperando legenda, {len(r['descartados'])} descartados, {r['restam']} ainda na fila")
            for chave in ("interrompido", "aviso"):
                if r.get(chave):
                    print(f"   {r[chave]}")
    elif args.cmd == "pendentes":
        print(f"{saida['total']} notas por destilar" + (f" (mostrando {len(saida['notas'])})" if saida["total"] > len(saida["notas"]) else ""))
        print("\n".join(f"  {n['publicado_em']} {n['arquivo']}" for n in saida["notas"]))
    elif args.cmd == "buscar":
        for n in saida:
            print(f"{n['publicado_em']} · {n['titulo']} · {n['canal']} · {n['relevancia']} · {', '.join(n['temas'])}\n  {n['arquivo']}")
            if args.itens:
                print(n[BASE["itens"]] + "\n")
        print(f"{len(saida)} notas")
    elif args.cmd == "validar":
        print("\n".join(saida["erros"]) or f"ok: {saida['notas']} notas conferidas")
    else:
        print(json.dumps(saida, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    sys.exit(main())
