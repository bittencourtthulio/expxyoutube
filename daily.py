"""Daily: a conversa do Usuário com a equipe do canal, e a ata de cada dia.

O Usuário escreve pelo painel (`python3 painel.py`) ou por aqui. A rotina da manhã lê o que
está pendente, executa ou estrutura no harness, e responde no mesmo fio. Tudo fica em
estado/daily.jsonl, um evento por linha, só acréscimo: nada se edita e nada se apaga.

Quatro tipos de item:
  tarefa        algo para a rotina fazer           aberta -> fazendo -> feita | recusada | cancelada
  nao-fazer     proibição que vale até ser revogada  ativa -> aplicada -> revogada
  aprendizado   orientação que vale até ser revogada ativa -> aplicada -> revogada
  pergunta      dúvida ou comentário               aberta -> respondida | cancelada

"ativa" já está em vigor: a rotina obedece desde a primeira leitura. "aplicada" quer dizer que
a rotina já estruturou aquilo no harness (regra em editorial/**, rule, cadência) e
disse onde. Cancelar e revogar são só do Usuário.
O aceite encerra tarefas; em aprendizados/proibições, conclui a implantação com "aplicada",
sem revogar a regra. Todo o histórico é preservado.

  python3 daily.py novo --tipo nao-fazer --texto "Não use clickbait no título" [--para roteirista] [--serie shorts]
  python3 daily.py pendentes            # o que a rotina tem que executar ou responder (é o que o cron pergunta)
  python3 daily.py regras [--serie X]   # proibições e aprendizados em vigor: leia antes de planejar, escrever ou revisar
  python3 daily.py responder d003 --autor analista --texto "..." [--status feita] [--onde "editorial/voz.md, commit abc123"]
  python3 daily.py revogar d003 | cancelar d003 [--motivo "..."]
  python3 daily.py finalizar d003      # aceite do Usuário; arquiva sem apagar o fio
  python3 daily.py lista [--tudo]       # todos os fios
  python3 daily.py dia [AAAA-MM-DD]     # a ata do dia: análise, plano, decisões, produção e a conversa
  python3 daily.py kpis                 # KPIs do canal na análise mais recente (é o que o painel mostra)
  python3 daily.py saude                # eventos lidos e linhas corrompidas do log

"serie" é um recorte opcional: formato (shorts, video-longo) ou nome de playlist.
Todo comando aceita --json.
"""
import argparse
import fcntl
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import comum
import dashboard

RAIZ = Path(__file__).resolve().parent

TIPOS = {
    "tarefa": {"inicial": "aberta", "rotina": ("fazendo", "feita", "recusada"), "usuario": ("cancelada",)},
    "pergunta": {"inicial": "aberta", "rotina": ("respondida",), "usuario": ("cancelada",)},
    "nao-fazer": {"inicial": "ativa", "rotina": ("aplicada",), "usuario": ("revogada",)},
    "aprendizado": {"inicial": "ativa", "rotina": ("aplicada",), "usuario": ("revogada",)},
}
EQUIPE = ("planejador", "analista", "roteirista", "curador", "bibliotecario", "reviewer", "apresentador", "validador")  # mesma ordem de chat.EQUIPE
PARA = EQUIPE + ("ambos", "todos")
ABERTOS = ("aberta", "fazendo", "ativa")        # a rotina ainda deve algo
EM_VIGOR = ("ativa", "aplicada", "fazendo", "aguardando")                # proibição ou aprendizado que continua valendo
ENCERRADOS = ("cancelada", "revogada", "finalizada")
USUARIO = "usuario"


class Erro(Exception):
    pass


def arquivo():
    return RAIZ / "estado" / "daily.jsonl"   # resolvido na hora: acompanha a raiz (os testes usam outra)


def agora():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def eventos():
    """Eventos válidos do log. Linha corrompida é pulada (e contada em `saude()`), nunca derruba a leitura."""
    return comum.ler_jsonl(arquivo())[0]


def saude():
    evs, corrompidas = comum.ler_jsonl(arquivo())
    return {"eventos": len(evs), "corrompidas": corrompidas}


def _validos(linhas):
    saida = []
    for l in linhas:
        if not l.strip():
            continue
        try:
            e = json.loads(l)
        except ValueError:
            continue
        if isinstance(e, dict):
            saida.append(e)
    return saida


def _gravar(monta):
    """Acrescenta um evento com o arquivo travado. `monta` recebe os eventos já gravados."""
    caminho = arquivo()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a+", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        ja = _validos(f.read().splitlines())
        evento = monta(ja)
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")
    return evento


def itens(evs=None):
    """Estado de cada fio, derivado do log. Ordem: o mais novo primeiro."""
    fios = {}
    for e in evs if evs is not None else eventos():
        if e.get("evento") == "novo" and e.get("tipo") in TIPOS:
            fios[e["id"]] = {"id": e["id"], "tipo": e["tipo"], "para": e.get("para", "ambos"), "serie": e.get("serie"),
                             "data_inicio": e.get("data_inicio"), "data_final": e.get("data_final"), "titulo": e.get("titulo"), "texto": e["texto"], "criado_em": e["quando"], "status": TIPOS[e["tipo"]]["inicial"],
                             "revisao": 0, "edicoes": [], "onde": None, "mensagens": [{"quando": e["quando"], "autor": USUARIO, "texto": e["texto"]}]}
            continue
        fio = fios.get(e.get("id"))
        if not fio:
            continue
        fio["revisao"] += 1
        if e["evento"] == "edicao":
            fio.update(e["campos"])
            fio["edicoes"].append({"quando": e["quando"], "autor": e["autor"], "campos": e["campos"]})
        elif e["evento"] == "mover":
            fio["coluna"] = e["coluna"]
        elif e.get("status"):
            fio.pop("coluna", None)
        elif e["evento"] == "resposta":
            if aguarda_usuario(e):
                fio.pop("coluna", None)
            elif e.get("autor") == USUARIO and (fio.get("coluna") == "aguardando-resposta" or fio["status"] == "aguardando"):
                fio.pop("coluna", None)
                fio["status"] = TIPOS[fio["tipo"]]["inicial"]
        if e.get("texto"):
            fio["mensagens"].append({k: e[k] for k in ("quando", "autor", "texto", "ao_vivo", "onde", "aguarda_usuario") if k in e})
        if e.get("status"):
            fio["status"] = e["status"]
        if e.get("onde"):
            fio["onde"] = e["onde"]
        fio["atualizado_em"] = e["quando"]
    for fio in fios.values():
        fio.setdefault("atualizado_em", fio["criado_em"])
        fio["aguarda_usuario"] = fio["status"] not in ENCERRADOS and aguarda_usuario(fio["mensagens"][-1])
        fio["aguarda_rotina"] = fio["status"] not in ENCERRADOS and (
            fio["status"] in ABERTOS or fio["mensagens"][-1]["autor"] == USUARIO) and not fio["aguarda_usuario"]
        if fio["status"] == "aguardando":
            fio["aguarda_usuario"] = True
            fio["aguarda_rotina"] = False
        if fio.get("coluna"):
            fio["aguarda_usuario"] = fio["coluna"] == "aguardando-resposta"
            fio["aguarda_rotina"] = fio["coluna"] in ("pendente", "executando")
        fio["situacao"] = fio.get("coluna") or (
            "finalizado" if fio["status"] in ENCERRADOS else
            "aguardando-resposta" if fio["aguarda_usuario"] else
            "executando" if fio["status"] == "fazendo" else
            "pendente" if fio["aguarda_rotina"] else "finalizado")
        fio["revisar_em"] = (date.fromisoformat(fio["data_final"]) + timedelta(days=1)).isoformat() if fio.get("data_final") else None
        fio["regra_em_vigor"] = fio["tipo"] in ("nao-fazer", "aprendizado") and fio["status"] in EM_VIGOR
    return sorted(fios.values(), key=lambda f: f["id"], reverse=True)


def item(ident, evs=None):
    for fio in itens(evs):
        if fio["id"] == ident:
            return fio
    raise Erro(f"não existe item {ident} na daily. Veja `python3 daily.py lista --tudo`.")


def novo(tipo, texto, para="ambos", serie=None, titulo=None, data_inicio=None, data_final=None):
    data_inicio, data_final = validar_datas(data_inicio, data_final)
    titulo = (titulo or "").strip()
    if len(titulo) > 120:
        raise Erro("o título deve ter até 120 caracteres.")
    texto = (texto or "").strip()
    if tipo not in TIPOS:
        raise Erro(f"tipo '{tipo}' não existe. Use: {', '.join(TIPOS)}.")
    if para not in PARA:
        raise Erro(f"destinatário '{para}' não existe. Use: {', '.join(PARA)}.")
    if not texto:
        raise Erro("o item precisa de texto.")

    def monta(ja):
        n = sum(1 for e in ja if e.get("evento") == "novo") + 1
        return {"quando": agora(), "autor": USUARIO, "evento": "novo", "id": f"d{n:03d}", "tipo": tipo, "para": para,
                "serie": serie or None, "texto": texto, "titulo": titulo or None,
                "data_inicio": data_inicio, "data_final": data_final}
    return _gravar(monta)


_NAO_INFORMADO = object()


def validar_datas(inicio, final):
    for valor in (inicio, final):
        if valor:
            try:
                if not isinstance(valor, str) or date.fromisoformat(valor).isoformat() != valor:
                    raise ValueError()
            except (ValueError, TypeError):
                raise Erro("use datas válidas no formato AAAA-MM-DD.")
    if inicio and final and final < inicio:
        raise Erro("a data final não pode ser anterior à data de início.")
    return inicio or None, final or None


def editar(ident, titulo, texto, revisao=None, data_inicio=_NAO_INFORMADO, data_final=_NAO_INFORMADO):
    if not isinstance(titulo, str) or not titulo.strip() or len(titulo.strip()) > 120:
        raise Erro("informe um título de até 120 caracteres.")
    if not isinstance(texto, str) or not texto.strip():
        raise Erro("a descrição não pode ficar vazia.")
    def monta(ja):
        fio = item(ident, ja)
        if revisao is not None and revisao != fio["revisao"]:
            raise Erro("A tarefa mudou desde que você abriu. Reabra o modal para revisar antes de salvar.")
        inicio, final = validar_datas(fio.get("data_inicio") if data_inicio is _NAO_INFORMADO else data_inicio,
                                       fio.get("data_final") if data_final is _NAO_INFORMADO else data_final)
        return {"quando": agora(), "autor": USUARIO, "evento": "edicao", "id": ident,
                "campos": {"titulo": titulo.strip(), "texto": texto.strip(), "data_inicio": inicio, "data_final": final}}
    return _gravar(monta)


def mover(ident, coluna, revisao=None):
    if coluna not in ("pendente", "executando", "aguardando-resposta", "finalizado"):
        raise Erro("coluna inválida.")
    def monta(ja):
        fio = item(ident, ja)
        if revisao is not None and revisao != fio["revisao"]:
            raise Erro("A tarefa mudou. Atualize o quadro e tente novamente.")
        status = TIPOS[fio["tipo"]]["inicial"]
        if coluna == "finalizado":
            status = "aplicada" if fio["tipo"] in ("nao-fazer", "aprendizado") else "finalizada"
        elif coluna == "executando":
            status = "fazendo"
        elif coluna == "aguardando-resposta":
            status = "aguardando"
        return {"quando": agora(), "autor": USUARIO, "evento": "mover", "id": ident,
                "coluna": coluna, "status": status}
    return _gravar(monta)


def responder(ident, texto, autor="rotina", status=None, onde=None, ao_vivo=False, aguarda_resposta=None):
    texto = (texto or "").strip()
    if not texto:
        raise Erro("a resposta precisa de texto.")

    def monta(ja):
        fio = item(ident, ja)
        if fio["status"] in ENCERRADOS:
            raise Erro(f"{ident} está '{fio['status']}': o Usuário encerrou esse fio.")
        if status:
            quem = "usuario" if autor == USUARIO else "rotina"
            if status not in TIPOS[fio["tipo"]][quem]:
                raise Erro(f"status '{status}' não vale para {fio['tipo']} vindo de {autor}. Use: {', '.join(TIPOS[fio['tipo']][quem])}.")
        evento = {"quando": agora(), "autor": autor, "evento": "resposta", "id": ident, "texto": texto}
        if status:
            evento["status"] = status
        if onde:
            evento["onde"] = onde
        if aguarda_resposta is not None:
            evento["aguarda_usuario"] = bool(aguarda_resposta)
        if ao_vivo:
            evento["ao_vivo"] = True
        return evento
    return _gravar(monta)


def encerrar(ident, motivo=None):
    """Cancelar (tarefa, pergunta) ou revogar (nao-fazer, aprendizado). Só o Usuário."""
    def monta(ja):
        fio = item(ident, ja)
        if fio["status"] in ENCERRADOS:
            raise Erro(f"{ident} já está '{fio['status']}'.")
        evento = {"quando": agora(), "autor": USUARIO, "evento": "status", "id": ident, "status": TIPOS[fio["tipo"]]["usuario"][0]}
        if motivo:
            evento["texto"] = motivo.strip()
        return evento
    return _gravar(monta)


def aguarda_usuario(mensagem):
    """Eventos antigos usam a pergunta como fallback; novos podem declarar a espera."""
    return mensagem.get("autor") not in (USUARIO, "painel") and not mensagem.get("erro") and bool(
        mensagem.get("aguarda_usuario", "?" in mensagem.get("texto", "")))


def finalizar(ident):
    """Aceite explícito do Usuário: arquiva o item sem apagar a conversa."""
    def monta(ja):
        fio = item(ident, ja)
        if fio["status"] in ENCERRADOS:
            raise Erro(f"{ident} já está '{fio['status']}'.")
        status = "aplicada" if fio["tipo"] in ("aprendizado", "nao-fazer") else "finalizada"
        return {"quando": agora(), "autor": USUARIO, "evento": "mover", "id": ident, "status": status, "coluna": "finalizado"}
    return _gravar(monta)


def pendentes(para=None):
    fios = [f for f in itens() if f["aguarda_rotina"] and (not para or f["para"] in (para, "ambos", "todos"))]
    return sorted(fios, key=lambda f: f["id"])


def revisar(data=None):
    """Fila da revisão diária; prazo vencido pede conferência, nunca encerra sozinho."""
    hoje = data or datetime.now().astimezone().date().isoformat()
    validar_datas(hoje, None)
    filas = {"verificar_conclusao": [], "em_execucao": [], "pendentes": [], "aguardando_usuario": []}
    for fio in itens():
        situacao = fio["situacao"]
        if situacao == "finalizado":
            continue
        grupo = "aguardando_usuario" if situacao == "aguardando-resposta" else (
            "verificar_conclusao" if fio["revisar_em"] and hoje >= fio["revisar_em"] else
            "em_execucao" if situacao == "executando" else "pendentes")
        filas[grupo].append(fio)
    return {"data": hoje, **filas}


def regras(serie=None):
    """O que está em vigor. Item com série vale só para ela; sem série, vale para todas."""
    fios = [f for f in itens() if f["tipo"] in ("nao-fazer", "aprendizado") and f["status"] in EM_VIGOR
            and (not serie or not f["serie"] or f["serie"] == serie)]
    return sorted(fios, key=lambda f: f["id"])


# ---------- a ata do dia: junta o que cada script já grava, sem copiar nada ----------

def _json(caminho, padrao=None):
    return comum.ler_json(caminho, padrao)


def _jsonl(caminho):
    return comum.ler_jsonl(caminho)[0]


def _relatorios():
    return RAIZ / "editorial" / "analises" / "relatorios"


def dias():
    """Todo dia que tem plano, análise, decisão ou conversa. O mais novo primeiro."""
    achados = {}

    def marca(data, campo):
        achados.setdefault(data, {"data": data, "plano": False, "analise": False, "decisoes": 0, "conversa": 0})
        achados[data][campo] = True if campo in ("plano", "analise") else achados[data][campo] + 1

    for p in (RAIZ / "planejamento").glob("20??-??-??.json"):
        marca(p.stem, "plano")
    for p in _relatorios().glob("20??-??-??"):
        if (p / "leitura.json").exists() or (p / "diagnostico.json").exists():
            marca(p.name, "analise")
    for d in _jsonl(RAIZ / "estado" / "decisoes.jsonl"):
        if d.get("quando"):
            marca(d["quando"][:10], "decisoes")
    for e in eventos():
        if e.get("quando"):
            marca(e["quando"][:10], "conversa")
    return sorted(achados.values(), key=lambda d: d["data"], reverse=True)


def montar_dia(data):
    plano = _json(RAIZ / "planejamento" / f"{data}.json")
    # A análise do dia é a que o plano usou de base; sem plano, a pasta com a data do dia.
    base = (plano or {}).get("analise_base") or f"editorial/analises/relatorios/{data}"
    pasta = RAIZ / base
    leitura = _json(pasta / "leitura.json")
    diagnostico = _json(pasta / "diagnostico.json", {}) or {}
    # O plano de um dia pode ter sido escrito na véspera: as decisões daquela rodada são dele.
    datas = {data, ((plano or {}).get("gerado_em") or data)[:10]}
    logs = {}
    for log in sorted((RAIZ / "planejamento" / "logs").glob(f"{data}_*.log")):
        linhas = log.read_text(encoding="utf-8", errors="replace").splitlines()
        logs[log.stem.split("_", 1)[1]] = linhas[-40:]
    return {
        "data": data,
        "plano": plano,
        "analise": {"pasta": base, "data": Path(base).name, "leitura": leitura,
                    "canal": diagnostico.get("canal"), "kpis": diagnostico.get("kpis"),
                    "videos": (diagnostico.get("videos") or [])[:5],
                    "tendencia": (diagnostico.get("tendencia") or [])[-14:]} if (leitura or diagnostico) else None,
        "decisoes": [d for d in _jsonl(RAIZ / "estado" / "decisoes.jsonl") if (d.get("quando") or "")[:10] in datas],
        "conversa": [f for f in itens() if any(m["quando"][:10] == data for m in f["mensagens"])],
        "logs": logs,
    }


def kpis():
    """Os KPIs do canal na análise mais recente que os tem, e a leitura que o analista fez deles."""
    for pasta in sorted(_relatorios().glob("20??-??-??"), reverse=True):
        diagnostico = _json(pasta / "diagnostico.json", {}) or {}
        if diagnostico.get("kpis"):
            leitura = _json(pasta / "leitura.json", {}) or {}
            return {"data": pasta.name, "coletado_em": diagnostico.get("coletado_em"), "canal": diagnostico.get("canal"),
                    "fuso_dos_dias": diagnostico.get("fuso_dos_dias"),
                    "kpis": diagnostico["kpis"], "dashboard": dashboard.montar(diagnostico),
                    "leitura": leitura.get("kpis"), "tese": leitura.get("tese")}
    return None


# ---------- CLI ----------

def _linha(fio):
    alvo = f" [{fio['serie']}]" if fio["serie"] else ""
    return f"{fio['id']}  {fio['tipo']:<11} {fio['status']:<10} para {fio['para']:<10}{alvo} {fio['texto']}"


def imprimir(resultado, como_json):
    if como_json:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return
    if isinstance(resultado, list):
        if not resultado:
            print("nada.")
        for fio in resultado:
            print(_linha(fio))
            for m in fio["mensagens"][1:]:
                print(f"      {m['quando'][:16]} {m['autor']}: {m['texto']}")
    elif "mensagens" in resultado:
        imprimir([resultado], False)
    elif "evento" in resultado:
        print(f"{resultado['id']}: {resultado['evento']} gravado" + (f" ({resultado['status']})" if resultado.get("status") else ""))
    else:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("novo", help="item novo do Usuário")
    n.add_argument("--tipo", required=True, choices=list(TIPOS))
    n.add_argument("--texto", required=True)
    n.add_argument("--para", default="ambos", choices=PARA)
    n.add_argument("--serie")
    p = sub.add_parser("pendentes", help="o que a rotina tem que executar ou responder")
    p.add_argument("--para", choices=[x for x in PARA if x != "ambos"])
    sub.add_parser("regras", help="proibições e aprendizados em vigor").add_argument("--serie")
    r = sub.add_parser("responder", help="resposta da rotina (ou do Usuário) num fio")
    r.add_argument("id")
    r.add_argument("--texto", required=True)
    r.add_argument("--autor", default="rotina", help="um agente da equipe, rotina ou usuario")
    r.add_argument("--status", help="fazendo | feita | recusada | respondida | aplicada")
    r.add_argument("--aguarda-resposta", action="store_true", default=None, help="aguarda posicionamento do Usuário")
    r.add_argument("--onde", help="onde aquilo virou estrutura no harness: arquivo, comando, commit")
    for nome in ("revogar", "cancelar", "finalizar"):
        x = sub.add_parser(nome, help="só o Usuário")
        x.add_argument("id")
        x.add_argument("--motivo")
    sub.add_parser("lista").add_argument("--tudo", action="store_true", help="inclui o que já foi encerrado")
    sub.add_parser("ver").add_argument("id")
    sub.add_parser("dia").add_argument("data", nargs="?")
    sub.add_parser("revisar", help="revisão de tarefas e entregas; não altera status").add_argument("--data")
    sub.add_parser("dias")
    sub.add_parser("kpis", help="KPIs do canal na análise mais recente")
    sub.add_parser("saude", help="eventos lidos e linhas corrompidas do log")
    for s in sub.choices.values():
        s.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    try:
        if args.cmd == "novo":
            r_ = novo(args.tipo, args.texto, args.para, args.serie)
        elif args.cmd == "pendentes":
            r_ = pendentes(args.para)
        elif args.cmd == "revisar":
            r_ = revisar(args.data)
        elif args.cmd == "regras":
            r_ = regras(args.serie)
        elif args.cmd == "responder":
            r_ = responder(args.id, args.texto, args.autor, args.status, args.onde, aguarda_resposta=args.aguarda_resposta)
        elif args.cmd in ("revogar", "cancelar"):
            r_ = encerrar(args.id, args.motivo)
        elif args.cmd == "finalizar":
            r_ = finalizar(args.id)
        elif args.cmd == "lista":
            r_ = [f for f in itens() if args.tudo or f["status"] not in ENCERRADOS]
        elif args.cmd == "ver":
            r_ = item(args.id)
        elif args.cmd == "dias":
            r_ = dias()
        elif args.cmd == "kpis":
            r_ = kpis()
        elif args.cmd == "saude":
            r_ = saude()
        else:
            r_ = montar_dia(args.data or datetime.now().astimezone().date().isoformat())
    except Erro as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    imprimir(r_, args.json or args.cmd in ("dia", "dias", "kpis", "saude"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
