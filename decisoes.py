"""Diário de decisões: o que a rotina ou a equipe decidiu, por quê e como desfazer.

    python3 decisoes.py registrar --tipo pauta --o-que "..." --por-que "..." --evidencia "..." --como-desfazer "..." \
        [--autor analista] [--daily d003]
    python3 decisoes.py lista [--limite 30] [--json]

Uma linha por decisão em estado/decisoes.jsonl, só por acréscimo. Toda ação que muda o harness
ou o plano, e toda ação vinda de um fio da daily (cite o dNNN), passa por aqui.
"""
import argparse
import json
import sys
from pathlib import Path

import comum

RAIZ = Path(__file__).resolve().parent
CAMPOS = ("tipo", "o_que", "por_que", "evidencia", "como_desfazer")


class Erro(Exception):
    pass


def arquivo():
    return RAIZ / "estado" / "decisoes.jsonl"


def registrar(tipo, o_que, por_que, evidencia, como_desfazer, autor="rotina", daily=None):
    valores = {"tipo": tipo, "o_que": o_que, "por_que": por_que, "evidencia": evidencia, "como_desfazer": como_desfazer}
    faltam = [c for c in CAMPOS if not (valores[c] or "").strip()]
    if faltam:
        raise Erro(f"faltam campos: {', '.join(faltam)}")
    evento = {"quando": comum.agora_iso(), "autor": autor, **{k: v.strip() for k, v in valores.items()}}
    if daily:
        evento["daily"] = daily
    comum.anexar_jsonl(arquivo(), evento)
    return evento


def lista(limite=None):
    evs = list(reversed(comum.ler_jsonl(arquivo())[0]))
    return evs[:limite] if limite else evs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("registrar")
    r.add_argument("--tipo", default="")
    r.add_argument("--o-que", default="")
    r.add_argument("--por-que", default="")
    r.add_argument("--evidencia", default="")
    r.add_argument("--como-desfazer", default="")
    r.add_argument("--autor", default="rotina")
    r.add_argument("--daily", help="id do fio da daily que originou a decisão (dNNN)")
    l_ = sub.add_parser("lista")
    l_.add_argument("--limite", type=int)
    l_.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "registrar":
            d = registrar(args.tipo, args.o_que, args.por_que, args.evidencia, args.como_desfazer, args.autor, args.daily)
            print(f"decisão registrada em {d['quando']}")
        else:
            itens = lista(args.limite)
            if args.json:
                print(json.dumps(itens, ensure_ascii=False, indent=2))
            else:
                for d in itens:
                    print(f"{d['quando'][:16]} [{d.get('tipo')}] {d.get('o_que')} (por {d.get('autor')})")
    except Erro as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
