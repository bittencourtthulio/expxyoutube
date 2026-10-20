"""Diagnóstico do canal a partir do retrato mais recente da coleta.

    .venv/bin/python editorial/analises/diagnostico.py [--retrato <arquivo>] [--saida <pasta>]
    .venv/bin/python editorial/analises/diagnostico.py validar-leitura [--pasta <relatorios/AAAA-MM-DD>]

Grava editorial/analises/relatorios/<hoje em SP>/diagnostico.json com os KPIs do canal
(objeto {id, nome, valor, anterior, variacao_pct, unidade, bom, nota}), as fichas de vídeo com
nota 0-10 por formato, formatos, tráfego e tendência. Métrica ausente fica None, nunca zero.
"""
import argparse
import statistics
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import comum  # noqa: E402

NOTA_VIEWS = ("O YouTube mudou a contagem de views em 2025 (Shorts) e em 2026 (todos os formatos); "
              "comparações que atravessam a mudança não são equivalentes. engaged_views mantém a regra antiga.")


def _v(valores, chave, sinal=False):
    return comum.valor((valores or {}).get(chave), sinal)


def _div(n, d, fator=1.0, casas=2):
    if n is None or d is None or d <= 0:
        return None
    return round(n / d * fator, casas)


def _soma(*vs):
    return None if any(v is None for v in vs) else sum(vs)


def _kpi(ident, nome, valor, anterior=None, unidade="", bom="sobe", nota=None):
    variacao = None
    if valor is not None and anterior:
        variacao = round(100 * (valor - anterior) / abs(anterior), 1)
    return {"id": ident, "nome": nome, "valor": valor, "anterior": anterior, "variacao_pct": variacao,
            "unidade": unidade, "bom": bom, "nota": nota}


def _medidas(v):
    """Números de uma janela com os nomes do harness."""
    views = _v(v, "views")
    ganhos, perdidos = _v(v, "subscribersGained"), _v(v, "subscribersLost")
    curtidas, comentarios, compart = _v(v, "likes"), _v(v, "comments"), _v(v, "shares")
    minutos = _v(v, "estimatedMinutesWatched")
    interacoes = _soma(curtidas, comentarios, compart)
    return {
        "views": views, "engaged_views": _v(v, "engagedViews"), "minutos": minutos,
        "horas_assistidas": round(minutos / 60, 1) if minutos is not None else None,
        "duracao_media": _v(v, "averageViewDuration"), "pct_assistido": _v(v, "averageViewPercentage"),
        "curtidas": curtidas, "comentarios": comentarios, "compartilhamentos": compart, "interacoes": interacoes,
        "inscritos_ganhos": ganhos, "inscritos_perdidos": perdidos,
        "saldo_inscritos": None if ganhos is None or perdidos is None else ganhos - perdidos,
        "playlists": _v(v, "videosAddedToPlaylists"),
        "taxa_engajamento": _div(interacoes, views, 100),
        "inscritos_por_mil_views": _div(ganhos, views, 1000),
        "minutos_por_view": _div(minutos, views),
        "playlists_por_mil_views": _div(_v(v, "videosAddedToPlaylists"), views, 1000),
    }


def kpis(retrato):
    jan = retrato.get("janelas") or {}
    atual_bruto = (jan.get("7d") or {}).get("valores")
    if not atual_bruto:
        return None
    a = _medidas(atual_bruto)
    b = _medidas((jan.get("7d_anteriores") or {}).get("valores"))
    t = _medidas((jan.get("30d") or {}).get("valores"))
    canal = retrato.get("canal") or {}
    pub = canal.get("publicacoes") or {}

    def par(chave, nome, unidade="", bom="sobe", nota=None):
        return _kpi(chave, nome, a[chave], b[chave], unidade, bom, nota)

    basicas = [
        _kpi("inscritos", "Inscritos", comum.valor(canal.get("inscritos")), nota="total do canal na coleta; a API arredonda"),
        par("inscritos_ganhos", "Inscritos ganhos", nota="inscrições na janela, todas as origens"),
        par("inscritos_perdidos", "Inscrições canceladas", bom="desce"),
        par("saldo_inscritos", "Saldo de inscritos", nota="ganhos menos cancelados"),
        par("views", "Views", nota=NOTA_VIEWS),
        par("engaged_views", "Views engajadas", nota="views pela regra antiga de contagem"),
        par("horas_assistidas", "Horas assistidas", "h"),
        _kpi("publicacoes", "Vídeos publicados", comum.valor(pub.get("7d")), comum.valor(pub.get("7d_anteriores")),
             nota="uploads públicos com data de publicação na janela"),
        par("curtidas", "Curtidas"),
        par("comentarios", "Comentários"),
        par("compartilhamentos", "Compartilhamentos"),
    ]
    performance = [
        par("taxa_engajamento", "Engajamento por view", "%", nota="(curtidas + comentários + compartilhamentos) ÷ views"),
        par("duracao_media", "Duração média assistida", "s"),
        par("pct_assistido", "Percentual médio assistido", "%"),
        par("inscritos_por_mil_views", "Inscritos por mil views"),
        par("minutos_por_view", "Minutos por view"),
        par("playlists_por_mil_views", "Adições a playlist por mil views"),
    ]
    recusadas = sorted({r.get("metrica") for j in jan.values() for r in (j.get("recusadas") or []) if r.get("metrica")})
    return {
        "janela": {k: jan["7d"].get(k) for k in ("desde", "ate")},
        "comparado_com": {k: (jan.get("7d_anteriores") or {}).get(k) for k in ("desde", "ate")},
        "basicas": basicas,
        "performance": performance,
        "trinta_dias": {k: t[k] for k in ("views", "horas_assistidas", "inscritos_ganhos", "saldo_inscritos", "interacoes")},
        "series": retrato.get("series") or {},
        "recusadas": recusadas,
    }


CAMPOS_FICHA = ("id", "titulo", "formato", "link", "publicado_em", "duracao_seg")
MEDIDAS_FICHA = ("views", "minutos", "duracao_media", "pct_assistido", "curtidas", "comentarios", "compartilhamentos", "inscritos")


def _grupo(formato):
    return "SHORTS" if formato == "SHORTS" else "VIDEOS"


def videos(retrato):
    """Fichas dos vídeos da janela de 28 dias, com nota = min(10, 5 × views ÷ mediana do mesmo formato)."""
    fichas = []
    for v in retrato.get("top_videos") or []:
        f = {c: v.get(c) for c in CAMPOS_FICHA}
        f.update({m: comum.valor(v.get(m)) for m in MEDIDAS_FICHA})
        f["interacoes"] = _soma(f["curtidas"], f["comentarios"], f["compartilhamentos"])
        f["taxa_engajamento"] = _div(f["interacoes"], f["views"], 100)
        f["inscritos_por_mil_views"] = _div(f["inscritos"], f["views"], 1000)
        fichas.append(f)
    medianas = {}
    for g in ("SHORTS", "VIDEOS"):
        vs = [f["views"] for f in fichas if _grupo(f["formato"]) == g and f["views"] is not None]
        medianas[g] = statistics.median(vs) if vs else None
    for f in fichas:
        m = medianas[_grupo(f["formato"])]
        f["mediana_do_formato"] = m
        f["nota"] = min(10, round(5 * f["views"] / m, 1)) if f["views"] is not None and m else None
    fichas.sort(key=lambda f: -(f["views"] if f["views"] is not None else -1))
    return fichas


def formatos(retrato):
    saida = {}
    for janela, linhas in (retrato.get("formatos") or {}).items():
        saida[janela] = []
        for l in linhas:
            inter = _soma(comum.valor(l.get("curtidas")), comum.valor(l.get("comentarios")), comum.valor(l.get("compartilhamentos")))
            saida[janela].append({**l, "interacoes": inter, "taxa_engajamento": _div(inter, comum.valor(l.get("views")), 100),
                                  "inscritos_por_mil_views": _div(comum.valor(l.get("inscritos")), comum.valor(l.get("views")), 1000)})
    return saida


def tendencia(retrato, dias=30):
    series = retrato.get("series") or {}
    mapas = {nome: {p["dia"]: p.get("valor") for p in pontos if p.get("dia")} for nome, pontos in series.items()}
    todos = sorted(set().union(*[set(m) for m in mapas.values()]) if mapas else set())[-dias:]
    return [{"dia": d, **{nome: comum.valor(m.get(d)) for nome, m in mapas.items()}} for d in todos]


def _retrato_mais_recente(raiz):
    pasta = Path(raiz) / "editorial" / "analises" / "dados" / "youtube"
    arquivos = sorted(pasta.glob("*.json"), key=lambda p: (p.name.split("_")[0], p.stat().st_mtime))
    if not arquivos:
        raise SystemExit(f"nenhum retrato em {pasta}; rode editorial/analises/coletar_youtube.py antes")
    return arquivos[-1]


def montar(raiz, caminho_retrato):
    retrato = comum.ler_json(caminho_retrato, {}) or {}
    try:
        rel = str(Path(caminho_retrato).resolve().relative_to(Path(raiz).resolve()))
    except ValueError:
        rel = str(caminho_retrato)
    return {
        "gerado_em": comum.agora_iso(),
        "retrato": rel,
        "coletado_em": retrato.get("coletado_em"),
        "fuso_dos_dias": retrato.get("fuso_dos_dias", "America/Los_Angeles"),
        "canal": retrato.get("canal") or {},
        "kpis": kpis(retrato),
        "videos": videos(retrato),
        "formatos": formatos(retrato),
        "trafego": retrato.get("trafego") or {},
        "tendencia": tendencia(retrato),
    }


def main(argv=None, raiz=None, hoje=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--retrato", help="retrato específico (padrão: o mais recente em dados/youtube)")
    ap.add_argument("--saida", help="pasta de saída (padrão: relatorios/<hoje em SP>)")
    args = ap.parse_args(argv)
    raiz = Path(raiz or RAIZ)
    caminho = Path(args.retrato) if args.retrato else _retrato_mais_recente(raiz)
    diag = montar(raiz, caminho)
    pasta = Path(args.saida) if args.saida else raiz / "editorial" / "analises" / "relatorios" / (hoje or comum.hoje_sp())
    destino = pasta / "diagnostico.json"
    comum.gravar_json(destino, diag)
    return destino



# ---------- leitura.json (escrita pelo analista) ----------

def _texto(v):
    return isinstance(v, str) and v.strip() != ""


def validar_leitura(pasta):
    """Lista de problemas do leitura.json da pasta; [] quando está no schema mínimo de D-15."""
    lt = comum.ler_json(Path(pasta) / "leitura.json")
    if not isinstance(lt, dict):
        return ["leitura.json ausente ou inválido"]
    erros = []
    if not _texto(lt.get("tese")):
        erros.append("tese: texto obrigatório")
    if "subtese" in lt and not isinstance(lt["subtese"], str):
        erros.append("subtese: precisa ser texto")
    for chave in ("kpis", "limites"):
        v = lt.get(chave)
        if not isinstance(v, list) or not all(_texto(x) for x in v):
            erros.append(f"{chave}: lista de textos obrigatória")
    achados = lt.get("achados")
    if not isinstance(achados, list):
        erros.append("achados: lista obrigatória")
    else:
        for i, a in enumerate(achados):
            for campo in ("titulo", "achado", "evidencia", "muda"):
                if not isinstance(a, dict) or not _texto(a.get(campo)):
                    erros.append(f"achados[{i}].{campo}: texto obrigatório")
    acoes = lt.get("acoes")
    if not isinstance(acoes, list):
        erros.append("acoes: lista obrigatória")
    else:
        for i, a in enumerate(acoes):
            if not (isinstance(a, list) and len(a) >= 2 and _texto(a[0]) and _texto(a[1])):
                erros.append(f"acoes[{i}]: precisa ser [ação, explicação]")
    cerebro = lt.get("cerebro")
    if cerebro is not None and not (isinstance(cerebro, dict) and all(isinstance(cerebro.get(k, []), list) for k in ("confirma", "questiona"))):
        erros.append("cerebro: precisa ter listas confirma e questiona")
    return erros


def validar_leitura_cli(argv=None, raiz=None):
    ap = argparse.ArgumentParser(prog="diagnostico.py validar-leitura")
    ap.add_argument("--pasta", help="pasta do relatório (padrão: relatorios/<hoje em SP>)")
    args = ap.parse_args(argv)
    pasta = Path(args.pasta) if args.pasta else Path(raiz or RAIZ) / "editorial" / "analises" / "relatorios" / comum.hoje_sp()
    erros = validar_leitura(pasta)
    for e in erros:
        print(f"erro: {e}")
    if not erros:
        print(f"ok: {pasta / 'leitura.json'}")
    return 1 if erros else 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "validar-leitura":
        sys.exit(validar_leitura_cli(sys.argv[2:]))
    print(main())
