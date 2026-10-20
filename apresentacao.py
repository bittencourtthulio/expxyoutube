"""Apresentações animadas do canal: deck, score, marca, render e palco.

    python3 apresentacao.py slug --titulo "..."               # slug único para um deck novo
    python3 apresentacao.py validar-deck <slug>               # confere deck.json contra o schema
    python3 apresentacao.py validar <slug> --score N --motivo "..." [--por validador]
    python3 apresentacao.py status <slug> aberta|gravada
    python3 apresentacao.py lista [--json]
    python3 apresentacao.py pauta --titulo ... --angulo ... --origem ... --score N --motivo ...
    python3 apresentacao.py referencia [--json]               # o que o público do canal já assiste
    python3 apresentacao.py candidatas [--json]               # pautas para o modo vazio
    python3 apresentacao.py marca <url> [--deck <slug>]       # identidade da ferramenta
    python3 apresentacao.py ler <url> [--json]                # texto limpo de uma página
    python3 apresentacao.py screenshot --deck <slug> [--url U] [--nome A] [--atualizar]
    python3 apresentacao.py render <slug>                     # MP4 e PNG por slide, capa e palco
    python3 apresentacao.py abrir <slug>                      # abre o palco no navegador

Um deck vive em apresentacoes/decks/<slug>/: deck.json (o apresentador escreve), estado.json (score e
status, só por este script), ativos/ (logo, screenshots) e saida/ (render). Nada aqui publica no canal.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

import comum

RAIZ = Path(__file__).resolve().parent
CODIGO = Path(__file__).resolve().parent      # o template do palco acompanha o código, não a raiz de dados
NVM = Path.home() / ".nvm" / "versions" / "node"
NODE_MINIMO = 18
SLUG_OK = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")


class Erro(ValueError):
    """Erro de entrada ou de estado: vira 400 no painel e mensagem no terminal."""


# ---------- pastas e estado ----------

def pasta_decks():
    return RAIZ / "apresentacoes" / "decks"


def pasta_do_deck(slug):
    if not isinstance(slug, str) or not SLUG_OK.fullmatch(slug):
        raise Erro(f"slug inválido: {slug!r}")
    return pasta_decks() / slug


def ler_deck(slug):
    arq = pasta_do_deck(slug) / "deck.json"
    if not arq.exists():
        raise Erro(f"deck não existe: {arq.relative_to(RAIZ)}")
    try:
        return json.loads(arq.read_text(encoding="utf-8"))
    except ValueError as e:
        raise Erro(f"deck.json inválido em {slug}: {e}")


def ler_estado(slug):
    arq = pasta_do_deck(slug) / "estado.json"
    if not arq.exists():
        return None
    try:
        return json.loads(arq.read_text(encoding="utf-8"))
    except ValueError as e:
        raise Erro(f"estado.json inválido em {slug}: {e}")


def gravar_estado(slug, estado):
    comum.gravar_json(pasta_do_deck(slug) / "estado.json", estado)
    return estado


# ---------- deck: schema e validação (D-46, D-47) ----------

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
ARQUIVO_DE_ATIVO = re.compile(r"^[\w.-]+\.(?:png|jpg|jpeg|webp|svg)$", re.I)
TRAVESSAO = "—"
MEIA_RISCA = "–"
FUNDO = "#16181A"
CONTRASTE_MINIMO = 3.0
TIPOS = {
    "titulo": {"kicker": 4, "titulo": 10, "subtitulo": 20},
    "declaracao": {"texto": 20, "autor": 4},
    "grade": {"titulo": 8}, "comparacao": {"titulo": 8}, "etapas": {"titulo": 8}, "estatisticas": {"titulo": 8}, "fluxo": {"titulo": 8},
    "screenshot": {"titulo": 6, "legenda": 12},
    "cta": {"titulo": 10, "texto": 16},
}
COM_DESTAQUE = {("titulo", "titulo"), ("declaracao", "texto")}
# slide é conteúdo da aula: views, inscritos e o diagnóstico do canal ficam no painel, nunca na tela
FONTE_DO_CANAL = re.compile(r"diagn[oó]stico|leitura\.json|inscritos|views|youtube analytics|nosso canal", re.I)


def _palavras(texto):
    return len(re.sub(r"</?b>", "", texto).split())


def _luminancia(hex6):
    def canal(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex6[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)


def contraste(a, b):
    la, lb = _luminancia(a), _luminancia(b)
    claro, escuro = max(la, lb), min(la, lb)
    return round((claro + 0.05) / (escuro + 0.05), 2)


def _texto(erros, onde, valor, limite, obrigatorio=True, destaque=False):
    if valor is None or valor == "":
        if obrigatorio:
            erros.append(f"{onde}: texto obrigatório")
        return
    if not isinstance(valor, str):
        erros.append(f"{onde}: precisa ser texto")
        return
    if TRAVESSAO in valor or MEIA_RISCA in valor:
        erros.append(f"{onde}: sem travessão nem meia-risca")
    if "\n" in valor:
        erros.append(f"{onde}: sem quebra de linha")
    if not destaque and "<b>" in valor:
        erros.append(f"{onde}: <b> só em título e declaração")
    if _palavras(valor) > limite:
        erros.append(f"{onde}: no máximo {limite} palavras (tem {_palavras(valor)})")


def _itens(erros, onde, itens, minimo, maximo, campos):
    if not isinstance(itens, list) or not minimo <= len(itens) <= maximo:
        erros.append(f"{onde}: de {minimo} a {maximo} itens")
        return
    for j, item in enumerate(itens):
        if not isinstance(item, dict):
            erros.append(f"{onde}[{j}]: precisa ser objeto")
            continue
        for campo, limite in campos.items():
            _texto(erros, f"{onde}[{j}].{campo}", item.get(campo), limite)


def _imagem(erros, onde, valor):
    if valor is None:
        return
    if not isinstance(valor, str) or not ARQUIVO_DE_ATIVO.fullmatch(valor):
        erros.append(f"{onde}: imagem é o nome de um arquivo dentro de ativos/ (png, jpg ou webp), sem barra")


def _slide(erros, i, s):
    onde = f"slides[{i}]"
    tipo = s.get("tipo") if isinstance(s, dict) else None
    if tipo not in TIPOS:
        erros.append(f"{onde}: tipo inválido {tipo!r}; use {', '.join(TIPOS)}")
        return
    for campo, limite in TIPOS[tipo].items():
        _texto(erros, f"{onde}.{campo}", s.get(campo), limite, obrigatorio=campo != "autor", destaque=(tipo, campo) in COM_DESTAQUE)
    if tipo == "grade":
        _itens(erros, f"{onde}.itens", s.get("itens"), 3, 6, {"titulo": 5, "texto": 14})
    elif tipo == "etapas":
        _itens(erros, f"{onde}.itens", s.get("itens"), 3, 5, {"titulo": 4, "texto": 10})
    elif tipo == "fluxo":
        nos = s.get("nos")
        if not isinstance(nos, list) or not 3 <= len(nos) <= 6:
            erros.append(f"{onde}.nos: de 3 a 6 nós")
        else:
            for j, no in enumerate(nos):
                if not isinstance(no, dict):
                    erros.append(f"{onde}.nos[{j}]: precisa ser objeto com titulo e texto")
                    continue
                _texto(erros, f"{onde}.nos[{j}].titulo", no.get("titulo"), 4)
                _texto(erros, f"{onde}.nos[{j}].texto", no.get("texto"), 8, obrigatorio=False)
    elif tipo == "comparacao":
        for lado in ("esquerda", "direita"):
            col = s.get(lado)
            if not isinstance(col, dict):
                erros.append(f"{onde}.{lado}: precisa ser objeto com titulo e itens")
                continue
            _texto(erros, f"{onde}.{lado}.titulo", col.get("titulo"), 4)
            itens = col.get("itens")
            if not isinstance(itens, list) or not 1 <= len(itens) <= 5:
                erros.append(f"{onde}.{lado}.itens: de 1 a 5 itens")
            else:
                for j, item in enumerate(itens):
                    _texto(erros, f"{onde}.{lado}.itens[{j}]", item, 8)
    elif tipo == "estatisticas":
        numeros = s.get("numeros")
        if not isinstance(numeros, list) or not 1 <= len(numeros) <= 4:
            erros.append(f"{onde}.numeros: de 1 a 4 números")
        else:
            for j, n in enumerate(numeros):
                if not isinstance(n, dict) or isinstance(n.get("valor"), bool) or not isinstance(n.get("valor"), (int, float)):
                    erros.append(f"{onde}.numeros[{j}].valor: precisa ser número")
                    continue
                _texto(erros, f"{onde}.numeros[{j}].rotulo", n.get("rotulo"), 4)
                if not isinstance(n.get("sufixo", ""), str):
                    erros.append(f"{onde}.numeros[{j}].sufixo: texto")
                if not isinstance(n.get("fonte"), str) or not n["fonte"].strip():
                    erros.append(f"{onde}.numeros[{j}].fonte: número só entra com fonte externa do tema (site, doc, nota com url)")
                elif FONTE_DO_CANAL.search(n["fonte"]):
                    erros.append(f"{onde}.numeros[{j}].fonte: métrica do nosso canal não entra em slide; o slide é conteúdo da aula")
    elif tipo == "screenshot":
        _imagem(erros, f"{onde}.imagem", s.get("imagem"))
    elif tipo == "cta":
        _imagem(erros, f"{onde}.imagem", s.get("imagem"))
        if s.get("url") != "example.com":
            erros.append(f"{onde}.url: o CTA é sempre example.com")


def validar_deck(d):
    """Lista de violações do schema (vazia = deck válido)."""
    erros = []
    if not isinstance(d, dict):
        return ["deck precisa ser um objeto JSON"]
    for campo in ("slug", "titulo", "criado_em", "gerado_por"):
        if not isinstance(d.get(campo), str) or not d[campo]:
            erros.append(f"{campo}: texto obrigatório")
    if d.get("pauta_id") is not None and not re.fullmatch(r"[0-9a-f]{12}", str(d["pauta_id"])):
        erros.append("pauta_id: 12 hex ou null")
    if not isinstance(d.get("pauta"), dict) or not d["pauta"].get("origem"):
        erros.append("pauta: objeto com origem")
    m = d.get("marca")
    if not isinstance(m, dict) or not m.get("nome"):
        erros.append("marca: objeto com nome, cor, cor_2, logo, site e origem")
    else:
        for campo in ("cor", "cor_2"):
            v = m.get(campo)
            if v is None and campo == "cor_2":
                continue
            if not isinstance(v, str) or not HEX.fullmatch(v):
                erros.append(f"marca.{campo}: cor no formato #RRGGBB")
        if isinstance(m.get("cor"), str) and HEX.fullmatch(m["cor"]) and contraste(m["cor"], FUNDO) < CONTRASTE_MINIMO:
            erros.append(f"marca.cor: contraste {contraste(m['cor'], FUNDO)}:1 sobre {FUNDO}; mínimo {CONTRASTE_MINIMO}:1")
        if m.get("logo") is not None:
            _imagem(erros, "marca.logo", m.get("logo"))
        if m.get("origem") not in ("tabela", "site", "canal"):
            erros.append("marca.origem: tabela, site ou canal")
    slides = d.get("slides")
    if not isinstance(slides, list) or not 6 <= len(slides) <= 10:
        erros.append(f"slides: de 6 a 10 slides (tem {len(slides) if isinstance(slides, list) else 0})")
        return erros
    if not isinstance(slides[0], dict) or slides[0].get("tipo") != "titulo":
        erros.append("slides: o primeiro slide é do tipo titulo")
    if not isinstance(slides[-1], dict) or slides[-1].get("tipo") != "cta":
        erros.append("slides: o último slide é do tipo cta")
    for i, s in enumerate(slides):
        _slide(erros, i, s)
    return erros


def slug(titulo, hoje=None):
    """AAAA-MM-DD-<titulo> até 60 caracteres, único na pasta de decks (D-04)."""
    import unicodedata
    hoje = hoje or comum.hoje_sp()
    base = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    base = base[: 60 - len(hoje) - 1].rstrip("-") or "apresentacao"
    candidato, n = f"{hoje}-{base}", 1
    while (pasta_decks() / candidato).exists():
        n += 1
        candidato = f"{hoje}-{base}-{n}"
    return candidato


def cmd_slug(args):
    print(slug(args.titulo))


def cmd_validar_deck(args):
    erros = validar_deck(ler_deck(args.slug))
    if erros:
        raise Erro(f"deck {args.slug} com {len(erros)} problema(s):\n  - " + "\n  - ".join(erros))
    print(f"deck {args.slug} válido: {len(ler_deck(args.slug)['slides'])} slides")


# ---------- estado, status, lista e fila (D-20, D-23, D-24, D-44, D-45) ----------

CORTE = 80
MOTIVO_MINIMO = 40
STATUS_DO_PAINEL = ("aberta", "gravada")


def _score(valor):
    if isinstance(valor, bool) or not isinstance(valor, (int, str)) or not str(valor).strip().lstrip("-").isdigit():
        raise Erro("score precisa ser inteiro de 0 a 100")
    n = int(valor)
    if not 0 <= n <= 100:
        raise Erro("score precisa ser inteiro de 0 a 100")
    return n


def _motivo(texto):
    if not isinstance(texto, str) or len(texto.strip()) < MOTIVO_MINIMO:
        raise Erro(f"motivo precisa ter pelo menos {MOTIVO_MINIMO} caracteres e citar os números da referência")
    return texto.strip()


def validar(slug, score, motivo, por="validador"):
    """Grava o score: >= 80 abre, < 80 descarta. Pode ser refeito; cada vez entra em validacoes."""
    ler_deck(slug)
    score, motivo = _score(score), _motivo(motivo)
    agora = comum.agora_iso()
    e = ler_estado(slug) or {"slug": slug, "gravado_em": None, "validacoes": [], "render": None}
    e.update(score=score, motivo=motivo, validado_em=agora, validado_por=por,
             status="aberta" if score >= CORTE else "descartada", gravado_em=None)
    e["validacoes"] = (e.get("validacoes") or []) + [{"em": agora, "score": score, "motivo": motivo, "por": por}]
    e.setdefault("render", None)
    return gravar_estado(slug, e)


def status(slug, novo):
    """Só aberta <-> gravada. Descartada não reabre por aqui: precisa de novo validar >= 80."""
    if novo not in STATUS_DO_PAINEL:
        raise Erro("status só pode ser aberta ou gravada")
    e = ler_estado(slug)
    if not e:
        raise Erro(f"{slug} ainda não tem score: rode validar antes")
    if e["status"] == "descartada":
        raise Erro(f"{slug} está descartada (score {e['score']}): só um novo validar com score >= {CORTE} reabre")
    e["status"] = novo
    e["gravado_em"] = comum.agora_iso() if novo == "gravada" else None
    return gravar_estado(slug, e)


def pauta_id(titulo, origem):
    import hashlib
    import unicodedata
    chave = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode().lower().strip()
    chave = re.sub(r"\s+", " ", chave)
    return hashlib.sha1(f"{chave}|{origem}".encode()).hexdigest()[:12]


def arquivo_da_fila():
    return RAIZ / "apresentacoes" / "fila.json"


def ler_fila():
    dados = comum.ler_json(arquivo_da_fila(), {}) or {}
    return sorted(dados.get("pautas") or [], key=lambda p: -p["score"])


def pauta(titulo, angulo, origem, score, motivo):
    """Registra na fila uma pauta validada (só >= 80). Mesma pauta (pauta_id) substitui a anterior."""
    score, motivo = _score(score), _motivo(motivo)
    if score < CORTE:
        raise Erro(f"pauta com score {score} fica fora da fila: só entra a partir de {CORTE}")
    if not titulo.strip() or not angulo.strip() or not origem.strip():
        raise Erro("titulo, angulo e origem são obrigatórios")
    pid = pauta_id(titulo, origem)
    pautas = [p for p in ler_fila() if p["pauta_id"] != pid]
    pautas.append({"pauta_id": pid, "titulo": titulo.strip(), "angulo": angulo.strip(), "origem": origem.strip(),
                   "score": score, "motivo": motivo, "registrada_em": comum.agora_iso()})
    comum.gravar_json(arquivo_da_fila(), {"pautas": sorted(pautas, key=lambda p: -p["score"])})
    return pid


def _resumo_do_deck(slug):
    d, e = ler_deck(slug), ler_estado(slug)
    return {"slug": slug, "titulo": d.get("titulo"), "marca": (d.get("marca") or {}).get("nome"), "slides": len(d.get("slides") or []),
            "criado_em": d.get("criado_em"), "pauta_id": d.get("pauta_id"), "score": (e or {}).get("score"), "motivo": (e or {}).get("motivo"),
            "status": (e or {}).get("status"), "validado_em": (e or {}).get("validado_em"), "gravado_em": (e or {}).get("gravado_em"),
            "render": (e or {}).get("render"), "capa": (pasta_do_deck(slug) / "saida" / "capa.png").exists(),
            "palco": (pasta_do_deck(slug) / "saida" / "palco.html").exists()}


def lista():
    """Galeria: abertas por score decrescente, gravadas, descartadas, decks sem score e a fila."""
    r = {"abertas": [], "gravadas": [], "descartadas": [], "sem_score": [], "fila": ler_fila()}
    for pasta in sorted(pasta_decks().glob("*/")):
        if not (pasta / "deck.json").exists():
            continue
        resumo = _resumo_do_deck(pasta.name)
        if resumo["status"] is None:
            r["sem_score"].append(pasta.name)
        else:
            r[resumo["status"] + "s"].append(resumo)
    for chave in ("abertas", "gravadas", "descartadas"):
        r[chave].sort(key=lambda d: (-d["score"], d["slug"]))
    return r


def cmd_validar(args):
    e = validar(args.slug, args.score, args.motivo, por=args.por)
    print(f"{args.slug}: score {e['score']} -> {e['status']}")


def cmd_status(args):
    e = status(args.slug, args.status)
    print(f"{args.slug}: {e['status']}")


def cmd_lista(args):
    r = lista()
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return
    for chave in ("abertas", "gravadas", "descartadas"):
        print(f"{chave} ({len(r[chave])})")
        for d in r[chave]:
            print(f"  {d['score']:3d}  {d['slug']}  {d['titulo']}  [{d['marca']}, {d['slides']} slides{', renderizado' if d['capa'] else ''}]")
    if r["sem_score"]:
        print("sem score: " + ", ".join(r["sem_score"]))
    print(f"fila ({len(r['fila'])})")
    for p in r["fila"]:
        print(f"  {p['score']:3d}  {p['titulo']}  ({p['origem']})")


def cmd_pauta(args):
    pid = pauta(args.titulo, args.angulo, args.origem, args.score, args.motivo)
    print(f"pauta {pid} na fila com score {int(args.score)}")


# ---------- referência do canal e candidatas (D-19, D-38, D-41, D-45) ----------

STOPWORDS = set("a o os as um uma uns umas de do da dos das em no na nos nas por para com sem que e ou se ao aos à às é são "
                "ser ter como mais menos muito seu sua seus suas meu minha este esta isso isto aquele aquela ele ela eles elas "
                "the of and to in on for with your my is it vs x".split())
TOP_VIEWS = 10
TOP_INSCRITOS = 5
VIEWS_MINIMAS = 100


def _palavras_do_titulo(titulo):
    import unicodedata
    texto = unicodedata.normalize("NFKD", titulo or "").encode("ascii", "ignore").decode().lower()
    return [p for p in re.findall(r"[a-z0-9]+", texto) if p not in STOPWORDS and len(p) > 1]


def diagnostico_mais_recente():
    pastas = sorted((RAIZ / "editorial" / "analises" / "relatorios").glob("20??-??-??"), reverse=True)
    for p in pastas:
        if (p / "diagnostico.json").exists():
            return p / "diagnostico.json"
    raise Erro("nenhum diagnostico.json em editorial/analises/relatorios/: rode /analisar-canal antes de pontuar")


def _ficha(v, mediana):
    views = comum.valor(v.get("views"))
    return {"id": v.get("id"), "titulo": v.get("titulo"), "formato": v.get("formato"), "link": v.get("link"), "publicado_em": v.get("publicado_em"),
            "views": views, "views_sobre_mediana": round(views / mediana, 2) if views is not None and mediana else None,
            "minutos": comum.valor(v.get("minutos")), "pct_assistido": comum.valor(v.get("pct_assistido")),
            "taxa_engajamento": comum.valor(v.get("taxa_engajamento")), "inscritos_por_mil_views": comum.valor(v.get("inscritos_por_mil_views")),
            "inscritos": comum.valor(v.get("inscritos")), "curtidas": comum.valor(v.get("curtidas")), "comentarios": comum.valor(v.get("comentarios")),
            "duracao_seg": comum.valor(v.get("duracao_seg")), "palavras": _palavras_do_titulo(v.get("titulo"))}


def referencia():
    """O que o público já assiste: top por views crus e top por inscritos por mil views, do diagnóstico mais recente."""
    import statistics
    arq = diagnostico_mais_recente()
    diag = comum.ler_json(arq, {}) or {}
    videos = [v for v in diag.get("videos") or [] if isinstance(v, dict)]
    mediana = {}
    for formato in {v.get("formato") or "VIDEO_ON_DEMAND" for v in videos}:
        do_formato = [v for v in videos if (v.get("formato") or "VIDEO_ON_DEMAND") == formato]
        # a mediana do diagnóstico (D-40 do harness) vale primeiro; sem ela, a mediana das views que estão aqui
        pronta = next((comum.valor(v.get("mediana_do_formato")) for v in do_formato if comum.valor(v.get("mediana_do_formato"))), None)
        vs = [x for x in (comum.valor(v.get("views")) for v in do_formato) if x is not None]
        mediana[formato] = pronta or (statistics.median(vs) if vs else None)
    fichas = [_ficha(v, mediana.get(v.get("formato") or "VIDEO_ON_DEMAND")) for v in videos]
    por_views = sorted((f for f in fichas if f["views"] is not None), key=lambda f: -f["views"])
    por_inscritos = sorted((f for f in fichas if f["views"] is not None and f["views"] >= VIEWS_MINIMAS and f["inscritos_por_mil_views"] is not None),
                           key=lambda f: -f["inscritos_por_mil_views"])
    return {"diagnostico": str(arq.relative_to(RAIZ)), "gerado_em": diag.get("gerado_em"), "canal": diag.get("canal") or {},
            "total_videos": len(fichas), "mediana": mediana, "top_views": por_views[:TOP_VIEWS],
            "top_inscritos": por_inscritos[:TOP_INSCRITOS], "todos": por_views}


def candidatas():
    """Pautas para o modo vazio: biblioteca (via planejar.pautas), top vídeos do canal e fila, sem as que já têm deck."""
    import planejar
    ref = referencia()
    com_deck = set()
    for pasta in pasta_decks().glob("*/"):
        if (pasta / "deck.json").exists():
            try:
                pid = ler_deck(pasta.name).get("pauta_id")
            except Erro:
                continue
            if pid:
                com_deck.add(pid)
    saida = {"biblioteca": [], "top_videos": [], "fila": [], "excluidas": sorted(com_deck), "referencia": ref["diagnostico"]}
    for p in planejar.pautas(limite=30):
        pid = pauta_id(p["titulo"], p["fonte"])
        if pid not in com_deck:
            saida["biblioteca"].append({**p, "pauta_id": pid, "origem": p["fonte"]})
    for v in ref["top_views"]:
        origem = f"top:{v['id']}"
        pid = pauta_id(v["titulo"] or "", origem)
        if pid not in com_deck:
            saida["top_videos"].append({"titulo": v["titulo"], "origem": origem, "pauta_id": pid, "views": v["views"],
                                        "views_sobre_mediana": v["views_sobre_mediana"], "inscritos_por_mil_views": v["inscritos_por_mil_views"],
                                        "pct_assistido": v["pct_assistido"], "palavras": v["palavras"], "link": v["link"]})
    saida["fila"] = [p for p in ler_fila() if p["pauta_id"] not in com_deck]
    return saida


def cmd_referencia(args):
    r = referencia()
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return
    print(f"referência: {r['diagnostico']} ({r['total_videos']} vídeos)")
    for chave, medida in (("top_views", "views"), ("top_inscritos", "inscritos_por_mil_views")):
        print(chave)
        for v in r[chave]:
            print(f"  {v[medida]!s:>8}  {v['formato']:<16} {v['titulo']}")


def cmd_candidatas(args):
    r = candidatas()
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return
    for chave in ("fila", "biblioteca", "top_videos"):
        print(f"{chave} ({len(r[chave])})")
        for p in r[chave]:
            print(f"  {p['pauta_id']}  {p['titulo']}  ({p['origem']})")


# ---------- marca da ferramenta (D-12, D-13, D-37) ----------

CANAL = {"nome": "CANAL", "cor": "#22C55E", "cor_2": "#4ADE80", "logo": None, "site": None, "origem": "canal"}
USER_AGENT = "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36 youtube-squad"
LIMITE_HTML = 2_000_000
ICONE_OK = re.compile(r"\.(?:png|jpg|jpeg|webp|svg)(?:\?.*)?$", re.I)


def buscar_html(url, timeout=20):
    """HTML de uma página com User-Agent de navegador (sites com Cloudflare devolvem vazio sem ele)."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(LIMITE_HTML).decode(r.headers.get_content_charset() or "utf-8", errors="replace")


def baixar(url, timeout=20):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(5_000_000)


def clarear(hex6, passo=0.10, minimo=CONTRASTE_MINIMO, fundo=FUNDO):
    """Mistura com branco em passos de 10% até o contraste passar do mínimo (D-12)."""
    cor = hex6.upper()
    for _ in range(12):
        if contraste(cor, fundo) >= minimo:
            return cor
        r, g, b = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
        r, g, b = (round(c + (255 - c) * passo) for c in (r, g, b))
        cor = f"#{r:02X}{g:02X}{b:02X}"
    return cor


def _saturacao(hex6):
    r, g, b = (int(hex6[i:i + 2], 16) / 255 for i in (1, 3, 5))
    mx, mn = max(r, g, b), min(r, g, b)
    return 0 if mx == 0 else (mx - mn) / mx


def sinais_do_html(html):
    """title, theme-color, ícone, og:image e a cor saturada mais frequente no HTML; ausente vira None, nunca erro."""
    from collections import Counter
    from html import unescape
    cabeca = html[:LIMITE_HTML]
    m = re.search(r"<title[^>]*>(.*?)</title>", cabeca, re.I | re.S)
    titulo = unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else None
    metas = {}
    for tag in re.findall(r"<meta\b[^>]*>", cabeca, re.I):
        nome = re.search(r'(?:name|property)\s*=\s*["\']([^"\']+)', tag, re.I)
        conteudo = re.search(r'content\s*=\s*["\']([^"\']*)', tag, re.I)
        if nome and conteudo:
            metas.setdefault(nome.group(1).lower(), unescape(conteudo.group(1)))
    icone = None
    for tag in re.findall(r"<link\b[^>]*>", cabeca, re.I):
        rel = re.search(r'rel\s*=\s*["\']([^"\']+)', tag, re.I)
        href = re.search(r'href\s*=\s*["\']([^"\']+)', tag, re.I)
        if rel and href and "icon" in rel.group(1).lower():
            icone = unescape(href.group(1))
            if "apple" not in rel.group(1).lower():
                break
    cores = Counter()
    for hexs in re.findall(r"#([0-9a-fA-F]{6})\b", cabeca):
        cor = "#" + hexs.upper()
        if _saturacao(cor) >= 0.35 and 0.06 < _luminancia(cor) < 0.9:
            cores[cor] += 1
    theme = metas.get("theme-color")
    theme = theme.upper() if theme and HEX.fullmatch(theme) else None
    return {"titulo": titulo, "theme_color": theme, "icone": icone, "og_image": metas.get("og:image"),
            "cores": [c for c, _ in cores.most_common(5)]}


def _nome_do_titulo(titulo):
    if not titulo:
        return None
    return re.split(r"\s+[|\-–—:·]\s+", titulo, maxsplit=1)[0].strip() or None


def tabela_de_marcas():
    return (comum.ler_json(RAIZ / "apresentacoes" / "comuns" / "marcas.json", {}) or {}).get("marcas") or {}


def marca_curada(url):
    from urllib.parse import urlparse
    host = (urlparse(url).hostname or "").lower()
    for chave, m in tabela_de_marcas().items():
        if any(host == h or host.endswith("." + h) for h in m.get("hosts") or []):
            return {"chave": chave, **m}
    return None


def marca(url, deck=None, buscar_html=None, baixar=None):
    """Identidade da ferramenta: tabela curada, depois sinais do site, senão CANAL. Nunca lança por falha de rede."""
    from urllib.parse import urljoin, urlparse
    buscar_html = buscar_html or globals()["buscar_html"]
    baixar = baixar or globals()["baixar"]
    site = f"{urlparse(url).scheme or 'https'}://{urlparse(url).hostname}" if urlparse(url).hostname else url
    saida = {**CANAL, "site": site, "icone": None, "avisos": []}
    curada = marca_curada(url)
    if curada:
        saida["nome"] = curada["nome"]
        if curada.get("cor"):
            saida.update(cor=curada["cor"].upper(), cor_2=None, origem="tabela")
    try:
        sinais = sinais_do_html(buscar_html(url))
    except Exception as e:  # rede, HTTP, decode: tudo vira aviso (base: extração tolerante)
        sinais = None
        saida["avisos"].append(f"não li o site ({type(e).__name__}: {str(e)[:80]}); identidade {saida['origem']}")
    if sinais:
        if not curada and sinais["titulo"]:
            saida["nome"] = _nome_do_titulo(sinais["titulo"]) or saida["nome"]
        if not curada:
            cor = sinais["theme_color"] or (sinais["cores"][0] if sinais["cores"] else None)
            if cor:
                saida.update(cor=clarear(cor), cor_2=None, origem="site")
        if sinais["icone"]:
            saida["icone"] = urljoin(url, sinais["icone"])
    if saida["cor"] == CANAL["cor"]:
        saida["cor_2"] = CANAL["cor_2"]
    if deck and saida["icone"]:
        if not ICONE_OK.search(saida["icone"]):
            saida["avisos"].append(f"ícone em formato sem suporte ({saida['icone']}); slide sai sem logo")
        else:
            try:
                dados = baixar(saida["icone"])
                pasta = pasta_do_deck(deck) / "ativos"
                pasta.mkdir(parents=True, exist_ok=True)
                sufixo = ".svg" if ICONE_OK.search(saida["icone"]).group(0).lower().startswith(".svg") else ".png"
                (pasta / f"logo{sufixo}").write_bytes(dados)
                saida["logo"] = f"logo{sufixo}"
            except Exception as e:
                saida["avisos"].append(f"não baixei o ícone ({type(e).__name__}); slide sai sem logo")
    return saida


def cmd_marca(args):
    m = marca(args.url, deck=args.deck)
    print(json.dumps(m, ensure_ascii=False, indent=1))


# ---------- ler <url> (D-15) ----------

LIMITE_TEXTO = 20_000
YOUTUBE = re.compile(r"(?:^|\.)(?:youtube\.com|youtu\.be)$", re.I)


def ler(url, buscar_html=None):
    """Texto limpo de uma página: título, descrição, h1-h3 e parágrafos, até 20 mil caracteres. Sem JS."""
    from html import unescape
    from urllib.parse import urlparse
    if YOUTUBE.search(urlparse(url).hostname or ""):
        raise Erro("vídeo do YouTube não entra por aqui: cadastre o canal e use python3 biblioteca.py importar (a biblioteca destila)")
    buscar_html = buscar_html or globals()["buscar_html"]
    try:
        html = buscar_html(url)
    except Exception as e:
        raise Erro(f"não consegui ler {url}: {type(e).__name__}: {str(e)[:120]}")
    sinais = sinais_do_html(html)
    corpo = re.sub(r"<(script|style|nav|footer|header|noscript|svg)\b.*?</\1\s*>", " ", html, flags=re.I | re.S)
    blocos = []
    for tag, conteudo in re.findall(r"<(h1|h2|h3|p|li)\b[^>]*>(.*?)</\1\s*>", corpo, flags=re.I | re.S):
        texto = unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", conteudo))).strip()
        if not texto:
            continue
        nivel = {"h1": "# ", "h2": "## ", "h3": "### ", "li": "- "}.get(tag.lower(), "")
        blocos.append(nivel + texto)
    texto, cortado = "\n".join(blocos), False
    if len(texto) > LIMITE_TEXTO:
        texto, cortado = texto[:LIMITE_TEXTO], True
    return {"url": url, "titulo": sinais["titulo"], "descricao": None, "blocos": blocos, "texto": texto, "cortado": cortado,
            **{"descricao": m.group(1) for m in [re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)', html, re.I)] if m}}


def cmd_ler(args):
    r = ler(args.url)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return
    print(f"# {r['titulo'] or args.url}\n" + (f"{r['descricao']}\n\n" if r["descricao"] else "\n") + r["texto"])
    if r["cortado"]:
        print(f"\n[cortado em {LIMITE_TEXTO} caracteres]")


# ---------- screenshot de sites (D-14, D-48) ----------

SITE_DO_CTA = "https://example.com"
ARQUIVO_DO_CTA = "cta.png"
TIMEOUT_SCREENSHOT = 60
SCRIPT_SCREENSHOT = """import base64, time
new_tab({url!r})
try:
    wait_for_load()
except Exception:
    time.sleep(6)   # site pesado em JS: o load pode não responder; a captura sai do que já renderizou
cdp("Emulation.setDeviceMetricsOverride", width=1920, height=1080, deviceScaleFactor=1, mobile=False)
time.sleep(3)
dados = cdp("Page.captureScreenshot", format="png")["data"]
DESTINO = {destino!r}
open(DESTINO, "wb").write(base64.b64decode(dados))
print("screenshot ok", DESTINO)
close_tab()
"""


def _browser_harness():
    return os.environ.get("APRESENTACAO_BH") or shutil.which("browser-harness")


def capturar_site(url, destino, timeout=None):
    """Roda o browser-harness por subprocesso. Devolve None se capturou, ou o motivo (aviso) se não."""
    exe = _browser_harness()
    if not exe or not Path(exe).exists():
        return "browser-harness não encontrado (instale ou aponte APRESENTACAO_BH)"
    script = SCRIPT_SCREENSHOT.format(url=url, destino=str(destino))
    try:
        r = subprocess.run([exe], input=script, capture_output=True, text=True, timeout=timeout or TIMEOUT_SCREENSHOT)
    except subprocess.TimeoutExpired:
        return f"captura de {url} passou do tempo limite de {timeout or TIMEOUT_SCREENSHOT} s (Chrome pediu Allow?)"
    except OSError as e:
        return f"não consegui rodar o browser-harness: {e}"
    if r.returncode != 0 or not Path(destino).exists():
        return f"captura de {url} falhou: {(r.stderr or r.stdout).strip()[-200:]}"
    return None


def screenshot(slug, url=None, nome=None, atualizar=False):
    """Captura um site 1920x1080 para ativos/ do deck. O site do CTA é cacheado em comuns/. Nunca lança por captura."""
    pasta = pasta_do_deck(slug)
    if not (pasta / "deck.json").exists():
        raise Erro(f"deck não existe: {slug}")
    url = url or SITE_DO_CTA
    nome = nome or (ARQUIVO_DO_CTA if url == SITE_DO_CTA else re.sub(r"[^a-z0-9]+", "-", url.split("//")[-1].lower()).strip("-")[:40] + ".png")
    if not ARQUIVO_DE_ATIVO.fullmatch(nome) or "/" in nome:
        raise Erro("nome do arquivo: só letras, números, ponto e hífen, terminando em .png")
    ativos = pasta / "ativos"
    ativos.mkdir(parents=True, exist_ok=True)
    saida = {"arquivo": None, "reusado": False, "avisos": []}
    if url == SITE_DO_CTA:
        cache = RAIZ / "apresentacoes" / "comuns" / ARQUIVO_DO_CTA
        if cache.exists() and not atualizar:
            saida["reusado"] = True
        else:
            cache.parent.mkdir(parents=True, exist_ok=True)
            aviso = capturar_site(url, cache)
            if aviso:
                saida["avisos"].append(aviso)
                return saida
        shutil.copyfile(cache, ativos / nome)
    else:
        aviso = capturar_site(url, ativos / nome)
        if aviso:
            saida["avisos"].append(aviso)
            return saida
    saida["arquivo"] = nome
    return saida


def cmd_screenshot(args):
    r = screenshot(args.deck, url=args.url, nome=args.nome, atualizar=args.atualizar)
    if r["arquivo"]:
        print(f"{args.deck}: ativos/{r['arquivo']}" + (" (reusado de comuns/)" if r["reusado"] else ""))
    for a in r["avisos"]:
        print(f"aviso: {a}; o slide sai sem imagem")


# ---------- palco (D-05, D-06) ----------

def palco_html(d):
    """O palco: um <video> por slide, setas, tela cheia com F, R repete; tudo embutido, abre por file:// e pelo painel."""
    from html import escape
    modelo = (CODIGO / "apresentacoes" / "palco.html").read_text(encoding="utf-8")
    n = len(d["slides"])
    videos = "\n".join(
        f'    <video src="slide-{i:02d}.mp4" poster="slide-{i:02d}.png" preload="{"auto" if i <= 2 else "metadata"}" muted playsinline'
        f' aria-label="slide {i} de {n}: {escape(str(s.get("titulo") or s.get("texto") or s.get("tipo")))}"></video>'
        for i, s in enumerate(d["slides"], 1))
    cor = (d.get("marca") or {}).get("cor") or CANAL["cor"]
    return (modelo.replace("__TITULO__", escape(str(d.get("titulo") or d.get("slug") or "Apresentação")))
            .replace("__MARCA__", escape(str((d.get("marca") or {}).get("nome") or "CANAL")))
            .replace("__TOTAL__", f"{n:02d}").replace("__COR__", cor if HEX.fullmatch(cor) else CANAL["cor"]).replace("__VIDEOS__", videos))


# ---------- node e npm ----------

def _versao_do_node(caminho):
    try:
        saida = subprocess.run([caminho, "--version"], capture_output=True, text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.match(r"v?(\d+)", saida)
    return int(m.group(1)) if m else None


def achar_node():
    """APRESENTACAO_NODE, depois o PATH, depois a versão mais nova do nvm. Exige node >= 18."""
    candidatos = []
    if os.environ.get("APRESENTACAO_NODE"):
        candidatos.append(os.environ["APRESENTACAO_NODE"])
    else:
        no_path = shutil.which("node")
        if no_path:
            candidatos.append(no_path)
        if NVM.is_dir():
            versoes = sorted((p for p in NVM.glob("v*/bin/node")),
                             key=lambda p: [int(x) for x in p.parts[-3][1:].split(".") if x.isdigit()], reverse=True)
            candidatos += [str(p) for p in versoes]
    for c in candidatos:
        v = _versao_do_node(c)
        if v is not None and v >= NODE_MINIMO:
            return c
        if v is not None:
            raise Erro(f"node {v} em {c}: precisa de node >= {NODE_MINIMO} (nvm ou APRESENTACAO_NODE)")
    raise Erro("node não encontrado: instale o Node 20 pelo nvm ou aponte APRESENTACAO_NODE")


def achar_npm(node):
    return os.environ.get("APRESENTACAO_NPM") or str(Path(node).with_name("npm"))


# ---------- render, capa e abrir (D-10, D-22, D-48, D-49) ----------

TIMEOUT_NPM = 600
TIMEOUT_RENDER = 1800


def pasta_motion():
    return RAIZ / "apresentacoes" / "motion"


def _deck_para_render(slug, d):
    """Cópia do deck com imagem citada e ausente em ativos/ trocada por null (D-48). O deck.json não muda."""
    import copy
    avisos, ativos = [], pasta_do_deck(slug) / "ativos"
    d = copy.deepcopy(d)

    def confere(onde, nome):
        if nome and not (ativos / nome).is_file():
            avisos.append(f"{onde}: ativos/{nome} não existe; slide sai sem imagem")
            return None
        return nome
    if isinstance(d.get("marca"), dict):
        d["marca"]["logo"] = confere("marca.logo", d["marca"].get("logo"))
    for i, s in enumerate(d.get("slides") or []):
        if isinstance(s, dict) and "imagem" in s:
            s["imagem"] = confere(f"slides[{i}].imagem", s.get("imagem"))
    return d, avisos


def _garante_node_modules(node):
    if (pasta_motion() / "node_modules").is_dir():
        return False
    npm = achar_npm(node)
    print("instalando o projeto Remotion (primeira vez, precisa de rede)...", flush=True)
    r = subprocess.run([npm, "install"], cwd=pasta_motion(), capture_output=True, text=True, timeout=TIMEOUT_NPM)
    if r.returncode != 0:
        raise Erro(f"npm install falhou: {(r.stderr or r.stdout).strip()[-300:]}")
    return True


def render(slug):
    """Um MP4 e um PNG por slide, capa.png (slide 1) e palco.html. Exige score >= 80 e deck válido."""
    import time
    d = ler_deck(slug)
    e = ler_estado(slug)
    if not e:
        raise Erro(f"{slug} ainda não tem score: o validador precisa rodar validar antes do render (D-22)")
    if e["status"] == "descartada":
        raise Erro(f"{slug} está descartada (score {e['score']}): deck descartado não é renderizado (D-21)")
    erros = validar_deck(d)
    if erros:
        raise Erro(f"deck {slug} com {len(erros)} problema(s):\n  - " + "\n  - ".join(erros))
    if not (pasta_motion() / "scripts" / "render.mjs").exists():
        raise Erro("apresentacoes/motion/scripts/render.mjs não existe: o projeto Remotion não está no repositório")
    node = achar_node()
    _garante_node_modules(node)
    pasta = pasta_do_deck(slug)
    ativos, saida = pasta / "ativos", pasta / "saida"
    ativos.mkdir(exist_ok=True)
    saida.mkdir(exist_ok=True)
    para_render, avisos = _deck_para_render(slug, d)
    arq_deck = saida / "deck-render.json"
    comum.gravar_json(arq_deck, para_render)
    inicio = time.monotonic()
    print(f"renderizando {len(d['slides'])} slides de {slug}...", flush=True)
    try:
        r = subprocess.run([node, "scripts/render.mjs", str(arq_deck), str(saida), str(ativos)], cwd=pasta_motion(),
                           capture_output=True, text=True, timeout=TIMEOUT_RENDER)
        erro = None if r.returncode == 0 else (r.stderr.strip().splitlines() or r.stdout.strip().splitlines() or ["sem saída"])[-1]
        print(r.stdout.strip())
    except subprocess.TimeoutExpired:
        erro = f"render passou de {TIMEOUT_RENDER} s"
    except OSError as exc:
        erro = f"não consegui rodar o node: {exc}"
    segundos = round(time.monotonic() - inicio, 1)
    resultado = {"em": comum.agora_iso(), "slides": len(d["slides"]), "ok": erro is None, "avisos": avisos, "segundos": segundos, "erro": erro}
    if erro is None:
        faltam = [f"slide-{i:02d}.{ext}" for i in range(1, len(d["slides"]) + 1) for ext in ("mp4", "png") if not (saida / f"slide-{i:02d}.{ext}").exists()]
        if faltam:
            resultado.update(ok=False, erro="render terminou sem gravar " + ", ".join(faltam[:4]))
    if resultado["ok"]:
        shutil.copyfile(saida / "slide-01.png", saida / "capa.png")
        (saida / "palco.html").write_text(palco_html(d), encoding="utf-8")
    e["render"] = resultado
    gravar_estado(slug, e)
    for a in avisos:
        print(f"aviso: {a}")
    if not resultado["ok"]:
        raise Erro(f"render de {slug} falhou: {resultado['erro']}")
    print(f"pronto em {segundos} s: {saida.relative_to(RAIZ)}/palco.html")
    return resultado


def abrir(slug):
    palco = pasta_do_deck(slug) / "saida" / "palco.html"
    if not palco.exists():
        raise Erro(f"{slug} ainda não foi renderizado: rode render antes de abrir")
    url = palco.resolve().as_uri()
    webbrowser.open(url)
    return url


def cmd_render(args):
    render(args.slug)


def cmd_abrir(args):
    print(abrir(args.slug))


# ---------- CLI ----------

def _nao_implementado(args):
    raise Erro(f"{args.comando}: ainda não implementado")


def parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="comando", required=True)
    s = sub.add_parser("slug", help="slug único para um deck novo"); s.add_argument("--titulo", required=True)
    s = sub.add_parser("validar-deck", help="confere deck.json contra o schema"); s.add_argument("slug")
    s = sub.add_parser("validar", help="grava score e status"); s.add_argument("slug")
    s.add_argument("--score", required=True); s.add_argument("--motivo", required=True); s.add_argument("--por", default="validador")
    s = sub.add_parser("status", help="aberta ou gravada"); s.add_argument("slug"); s.add_argument("status")
    s = sub.add_parser("lista", help="galeria e fila"); s.add_argument("--json", action="store_true")
    s = sub.add_parser("pauta", help="registra pauta validada na fila")
    for campo in ("--titulo", "--angulo", "--origem", "--score", "--motivo"):
        s.add_argument(campo, required=True)
    s = sub.add_parser("referencia", help="top vídeos do canal"); s.add_argument("--json", action="store_true")
    s = sub.add_parser("candidatas", help="pautas para o modo vazio"); s.add_argument("--json", action="store_true")
    s = sub.add_parser("marca", help="identidade da ferramenta"); s.add_argument("url"); s.add_argument("--deck")
    s = sub.add_parser("ler", help="texto limpo de uma página"); s.add_argument("url"); s.add_argument("--json", action="store_true")
    s = sub.add_parser("screenshot", help="captura um site para os slides"); s.add_argument("--deck", required=True)
    s.add_argument("--url", default=None); s.add_argument("--nome", default=None); s.add_argument("--atualizar", action="store_true")
    s = sub.add_parser("render", help="MP4 e PNG por slide, capa e palco"); s.add_argument("slug")
    s = sub.add_parser("abrir", help="abre o palco no navegador"); s.add_argument("slug")
    return ap


COMANDOS = {"slug": cmd_slug, "validar-deck": cmd_validar_deck, "validar": cmd_validar, "status": cmd_status, "lista": cmd_lista, "pauta": cmd_pauta,
            "referencia": cmd_referencia, "candidatas": cmd_candidatas, "marca": cmd_marca, "ler": cmd_ler, "screenshot": cmd_screenshot,
            "render": cmd_render, "abrir": cmd_abrir}


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return COMANDOS.get(args.comando, _nao_implementado)(args) or 0
    except Erro as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
