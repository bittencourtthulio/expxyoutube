"""Consulta o cérebro de YouTube (cerebro/**) para a análise e para o plano do dia.

Junta, por tema, as práticas e as ressalvas das notas destiladas de relevância alta e média,
as mais novas primeiro, e grava um resumo que o analista cruza com o nosso dado. Usa a mesma
busca do `cerebro.py buscar`, no mesmo processo: não altera nada lá dentro.

  python3 editorial/analises/consultar_cerebro.py --para analise
  python3 editorial/analises/consultar_cerebro.py --para plano --saida planejamento/2026-09-20.cerebro.json
  python3 editorial/analises/consultar_cerebro.py --temas miniatura,retencao --limite 8

O que sai daqui é referência externa: opinião de criador, muitas vezes sem número. Vale como
hipótese para testar e contexto para planejar. Onde contradiz o que medimos, o nosso dado vence.
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import cerebro  # noqa: E402

PROPOSITOS = {
    # o que cada rotina precisa saber do cérebro
    "analise": ["algoritmo", "ctr", "miniatura", "titulo", "retencao", "shorts", "metricas", "cadencia", "tendencias"],
    "plano": ["ideias", "cadencia", "formato", "shorts", "titulo", "miniatura", "tendencias"],
    "roteiro": ["gancho", "retencao", "titulo", "miniatura", "seo-busca", "formato"],
}
PESO = {"alta": 0, "media": 1}


def buscar(tema, limite):
    if tema not in cerebro.temas_validos():
        raise SystemExit(f"tema '{tema}' não existe em cerebro/temas.json")
    achadas = cerebro.cmd_buscar(argparse.Namespace(tema=tema, canal=None, desde=None, texto=None, itens=True, limite=200))
    notas = [n for n in achadas if n.get("relevancia") in PESO and n.get("praticas")]
    notas.sort(key=lambda n: (PESO[n["relevancia"]], -int(str(n.get("publicado_em") or "0").replace("-", "")[:8] or 0)))
    return notas[:limite]


def praticas_do_tema(nota, tema):
    """Só as práticas marcadas com o tema pedido: uma nota cobre vários temas."""
    linhas = [l.strip() for l in str(nota["praticas"]).split("\n") if l.strip().startswith("-")]
    do_tema = [l for l in linhas if f"[{tema}]" in l]
    return [re.sub(r"\s+", " ", l.lstrip("- ")) for l in (do_tema or linhas[:2])]


def consultar(temas, limite):
    saida = {"gerado_em": datetime.now().astimezone().isoformat(timespec="seconds"), "temas": {}}
    for tema in temas:
        notas = buscar(tema, limite)
        saida["temas"][tema] = [{
            "titulo": n["titulo"], "canal": n["canal"], "publicado_em": n.get("publicado_em"), "relevancia": n["relevancia"],
            "url": n.get("url"), "arquivo": n.get("arquivo"), "praticas": praticas_do_tema(n, tema),
            "ressalvas": [re.sub(r"\s+", " ", l.lstrip("- ")) for l in str(n.get("ressalvas") or "").split("\n") if l.strip().startswith("-")][:3],
        } for n in notas]
    saida["notas_consultadas"] = len({x["arquivo"] for v in saida["temas"].values() for x in v})
    return saida


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--para", choices=sorted(PROPOSITOS), default="analise")
    ap.add_argument("--temas", help="lista separada por vírgula; sobrepõe --para")
    ap.add_argument("--limite", type=int, default=5, help="notas por tema")
    ap.add_argument("--saida", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    temas = [t.strip() for t in args.temas.split(",")] if args.temas else PROPOSITOS[args.para]
    res = consultar(temas, args.limite)
    res["para"] = args.para
    if args.saida:
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        args.saida.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0
    print(f"cérebro: {res['notas_consultadas']} notas consultadas em {len(temas)} temas\n")
    for tema, notas in res["temas"].items():
        print(f"## {tema}" + ("  (nada destilado com relevância alta ou média)" if not notas else ""))
        for n in notas:
            print(f"  · {n['canal']} {n['publicado_em']} [{n['relevancia']}] {n['titulo'][:80]}")
            for p in n["praticas"]:
                print(f"      - {p[:330]}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
