"""Plano do dia: o que a rotina da manhã entrega para o planejador decidir.

    python3 planejar.py criar [--data AAAA-MM-DD] [--refazer] [--json]
    python3 planejar.py nota --texto "..." [--data AAAA-MM-DD]
    python3 planejar.py ver [--data AAAA-MM-DD]

`criar` monta planejamento/<data>.json de forma determinística: a análise mais recente até a data
(KPIs e tese), os fios pendentes e as regras em vigor da daily, e as pautas mais novas da biblioteca
(relevância alta ou média). Quem decide e comenta é o planejador, com `nota`. Nada aqui produz ou
publica vídeo.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import comum
import daily

RAIZ = Path(__file__).resolve().parent
KPIS_DO_PLANO = ("views", "inscritos_ganhos", "saldo_inscritos", "horas_assistidas", "publicacoes", "taxa_engajamento",
                 "duracao_media", "inscritos_por_mil_views")
MAX_PAUTAS = 8
IDEIA = re.compile(r"^- \*\*(?P<titulo>.+?)\*\*\s*(?P<resto>.*)$")


class Erro(Exception):
    pass


def arquivo(data):
    return RAIZ / "planejamento" / f"{data}.json"


def _analise_base(data):
    pastas = sorted((RAIZ / "editorial" / "analises" / "relatorios").glob("20??-??-??"), reverse=True)
    for p in pastas:
        if p.name <= data and (p / "diagnostico.json").exists():
            return p
    return None


def _frontmatter(texto):
    if not texto.startswith("---\n"):
        return {}
    fim = texto.find("\n---", 4)
    cabeca = {}
    for linha in texto[4:fim].splitlines():
        if ":" not in linha:
            continue
        chave, valor = linha.split(":", 1)
        try:
            cabeca[chave.strip()] = json.loads(valor.strip())
        except ValueError:
            cabeca[chave.strip()] = valor.strip().strip('"')
    return cabeca


def _secao(texto, titulo):
    m = re.search(rf"^## {re.escape(titulo)}\n(.*?)(?=^## |\Z)", texto, flags=re.M | re.S)
    return m.group(1) if m else ""


def pautas(limite=MAX_PAUTAS):
    """Ideias das notas destiladas da biblioteca, relevância alta ou média, da nota mais nova para a mais antiga."""
    notas = []
    for arq in (RAIZ / "biblioteca" / "videos").glob("*/*.md"):
        texto = arq.read_text(encoding="utf-8", errors="replace")
        cab = _frontmatter(texto)
        if cab.get("status") != "destilado" or cab.get("relevancia") not in ("alta", "media"):
            continue
        notas.append((cab.get("publicado_em") or "", cab.get("relevancia"), arq, texto, cab))
    notas.sort(key=lambda n: (n[0], n[1] == "alta"), reverse=True)
    saida = []
    for publicado, relevancia, arq, texto, cab in notas:
        for linha in _secao(texto, "Ideias de conteúdo").splitlines():
            m = IDEIA.match(linha.strip())
            if not m:
                continue
            cabe = re.search(r"Cabe em:\s*([^.\[]+)", m.group("resto"))
            saida.append({"titulo": m.group("titulo").strip(), "angulo": m.group("resto").strip(),
                          "cabe_em": cabe.group(1).strip() if cabe else None, "relevancia": relevancia,
                          "video": cab.get("titulo"), "publicado_em": publicado,
                          "fonte": str(arq.relative_to(RAIZ))})
            if len(saida) >= limite:
                return saida
    return saida


def criar(data, refazer=False):
    destino = arquivo(data)
    anterior = comum.ler_json(destino)
    if anterior and not refazer:
        raise Erro(f"o plano de {data} já existe; use --refazer para montar de novo (as notas do planejador ficam)")
    base = _analise_base(data)
    diag = comum.ler_json(base / "diagnostico.json", {}) if base else {}
    leitura = comum.ler_json(base / "leitura.json", {}) if base else {}
    k = (diag or {}).get("kpis") or {}
    por_id = {x["id"]: x for x in (k.get("basicas") or []) + (k.get("performance") or [])}
    plano = {
        "data": data,
        "gerado_em": comum.agora_iso(),
        "analise_base": str(base.relative_to(RAIZ)) if base else None,
        "janela": k.get("janela"),
        "tese": (leitura or {}).get("tese"),
        "kpis": [{c: por_id[i].get(c) for c in ("id", "nome", "valor", "anterior", "variacao_pct", "unidade")}
                 for i in KPIS_DO_PLANO if i in por_id],
        "pendentes": [{"id": f["id"], "tipo": f["tipo"], "para": f["para"], "texto": f["texto"]} for f in daily.pendentes()],
        "regras": [{"id": f["id"], "tipo": f["tipo"], "serie": f["serie"], "texto": f["texto"]} for f in daily.regras()],
        "pautas": pautas(),
        "notas_do_planejador": (anterior or {}).get("notas_do_planejador", []),
    }
    comum.gravar_json(destino, plano)
    return plano


def nota(data, texto):
    texto = (texto or "").strip()
    if not texto:
        raise Erro("a nota precisa de texto")
    plano = comum.ler_json(arquivo(data))
    if not plano:
        raise Erro(f"não há plano de {data}; rode `python3 planejar.py criar --data {data}` antes")
    plano.setdefault("notas_do_planejador", []).append({"quando": comum.agora_iso(), "texto": texto})
    comum.gravar_json(arquivo(data), plano)
    return plano


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("criar")
    c.add_argument("--data")
    c.add_argument("--refazer", action="store_true")
    c.add_argument("--json", action="store_true")
    n = sub.add_parser("nota")
    n.add_argument("--texto", required=True)
    n.add_argument("--data")
    v = sub.add_parser("ver")
    v.add_argument("--data")
    args = ap.parse_args(argv)
    data = args.data or comum.hoje_sp()
    try:
        if args.cmd == "criar":
            plano = criar(data, args.refazer)
            if args.json:
                print(json.dumps(plano, ensure_ascii=False, indent=2))
            else:
                print(f"plano gravado em {arquivo(data).relative_to(RAIZ)}: {len(plano['pendentes'])} pendentes, "
                      f"{len(plano['regras'])} regras, {len(plano['pautas'])} pautas")
        elif args.cmd == "nota":
            nota(data, args.texto)
            print("nota registrada")
        else:
            plano = comum.ler_json(arquivo(data))
            if not plano:
                raise Erro(f"não há plano de {data}")
            print(json.dumps(plano, ensure_ascii=False, indent=2))
    except Erro as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
