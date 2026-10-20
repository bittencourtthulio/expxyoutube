"""Diagnóstico: KPIs no objeto de D-06, fichas de vídeo com nota por formato, retrato mais recente."""
import copy
import json

import pytest

import coletar_youtube as cy
import diagnostico as dg
from tests.falsos import YouTubeFalso


def valores(**kw):
    base = {"views": 1000, "engagedViews": 900, "estimatedMinutesWatched": 3000, "averageViewDuration": 180,
            "averageViewPercentage": 42.5, "likes": 50, "dislikes": 1, "comments": 20, "shares": 10,
            "subscribersGained": 30, "subscribersLost": 5, "videosAddedToPlaylists": 4}
    base.update(kw)
    return base


def retrato(atual=None, anterior=None):
    return {
        "coletado_em": "2026-09-23T10:00:00+00:00",
        "canal": {"id": "UC1", "titulo": "Canal", "handle": "@canal", "inscritos": 9630, "publicacoes": {"7d": 2, "7d_anteriores": 1}},
        "janelas": {
            "7d": {"desde": "2026-09-14", "ate": "2026-09-21", "valores": atual or valores(views=1100), "recusadas": []},
            "7d_anteriores": {"desde": "2026-09-07", "ate": "2026-09-14", "valores": anterior or valores(), "recusadas": []},
            "30d": {"desde": "2026-08-22", "ate": "2026-09-21", "valores": valores(views=4000, estimatedMinutesWatched=12000), "recusadas": [{"metrica": "engagedViews"}]},
        },
        "series": {"views": [{"dia": "2026-09-20", "valor": 100}], "inscritos_ganhos": [{"dia": "2026-09-20", "valor": 3}]},
    }


def por_id(k):
    return {x["id"]: x for x in k["basicas"] + k["performance"]}


def test_kpis_estrutura_e_janelas():
    k = dg.kpis(retrato())
    assert k["janela"] == {"desde": "2026-09-14", "ate": "2026-09-21"}
    assert k["comparado_com"] == {"desde": "2026-09-07", "ate": "2026-09-14"}
    assert set(k) >= {"basicas", "performance", "trinta_dias", "series", "recusadas"}
    assert k["recusadas"] == ["engagedViews"]
    assert k["series"]["views"][0]["valor"] == 100
    for kpi in k["basicas"] + k["performance"]:
        assert set(kpi) == {"id", "nome", "valor", "anterior", "variacao_pct", "unidade", "bom", "nota"}


def test_variacao_percentual_e_anterior_zero():
    k = por_id(dg.kpis(retrato()))
    assert k["views"]["valor"] == 1100 and k["views"]["anterior"] == 1000 and k["views"]["variacao_pct"] == 10.0
    r = retrato(atual=valores(shares=5), anterior=valores(shares=0))
    assert por_id(dg.kpis(r))["compartilhamentos"]["variacao_pct"] is None


def test_taxas_e_horas():
    k = por_id(dg.kpis(retrato()))
    assert k["taxa_engajamento"]["valor"] == round((50 + 20 + 10) / 1100 * 100, 2)
    assert k["taxa_engajamento"]["unidade"] == "%"
    assert k["horas_assistidas"]["valor"] == 50.0
    assert k["duracao_media"]["valor"] == 180 and k["duracao_media"]["unidade"] == "s"
    assert k["inscritos_por_mil_views"]["valor"] == round(30 / 1100 * 1000, 2)
    assert k["inscritos"]["valor"] == 9630 and k["inscritos"]["anterior"] is None
    assert k["publicacoes"]["valor"] == 2 and k["publicacoes"]["anterior"] == 1


def test_inscritos_perdidos_bom_desce_e_saldo_negativo_preservado():
    r = retrato(atual=valores(subscribersGained=10, subscribersLost=15), anterior=valores(subscribersGained=10, subscribersLost=5))
    k = por_id(dg.kpis(r))
    assert k["inscritos_perdidos"]["bom"] == "desce"
    assert k["saldo_inscritos"]["valor"] == -5 and k["saldo_inscritos"]["anterior"] == 5
    assert k["saldo_inscritos"]["variacao_pct"] == -200.0


def test_views_traz_nota_sobre_mudanca_de_contagem():
    k = por_id(dg.kpis(retrato()))
    assert "contagem" in (k["views"]["nota"] or "")


def test_metrica_ausente_fica_none_nunca_zero():
    atual = valores()
    del atual["shares"]
    k = por_id(dg.kpis(retrato(atual=atual)))
    assert k["compartilhamentos"]["valor"] is None
    assert k["taxa_engajamento"]["valor"] is None


def test_sem_valores_na_janela_kpis_none():
    r = retrato()
    r["janelas"]["7d"]["valores"] = {}
    assert dg.kpis(r) is None


def test_trinta_dias():
    t = dg.kpis(retrato())["trinta_dias"]
    assert t["views"] == 4000 and t["horas_assistidas"] == 200.0 and t["inscritos_ganhos"] == 30
    assert t["interacoes"] == 80


def top(vid, views, formato="VIDEO_ON_DEMAND"):
    return {"id": vid, "titulo": f"T {vid}", "formato": formato, "link": f"https://www.youtube.com/watch?v={vid}",
            "publicado_em": "2026-09-01", "duracao_seg": 600, "views": views, "minutos": views * 2, "duracao_media": 120,
            "pct_assistido": 30.0, "curtidas": 10, "comentarios": 2, "compartilhamentos": 1, "inscritos": 3}


def test_nota_por_formato_shorts_fora_da_mediana_dos_longos():
    r = retrato()
    r["top_videos"] = [top("a", 200), top("b", 100), top("c", 100), top("d", 50), top("s", 100000, "SHORTS")]
    fichas = {f["id"]: f for f in dg.videos(r)}
    # mediana dos longos = 100: o Short de 100 mil views não entra nela
    assert fichas["a"]["nota"] == 10 and fichas["b"]["nota"] == 5 and fichas["d"]["nota"] == 2.5
    assert fichas["s"]["nota"] == 5  # sozinho no grupo dele: está na própria mediana
    assert fichas["a"]["taxa_engajamento"] == round(13 / 200 * 100, 2)
    assert [f["id"] for f in dg.videos(r)][0] == "s"  # ordenado por views


def test_main_usa_retrato_mais_novo_mesmo_com_um_de_periodo_maior(tmp_path):
    pasta = tmp_path / "editorial" / "analises" / "dados" / "youtube"
    pasta.mkdir(parents=True)
    antigo = retrato(atual=valores(views=1))
    novo = retrato(atual=valores(views=2222))
    (pasta / "2026-09-22T2247_90d.json").write_text(json.dumps(antigo))
    (pasta / "2026-09-23T0401_30d.json").write_text(json.dumps(novo))
    destino = dg.main([], raiz=tmp_path, hoje="2026-09-23")
    assert destino == tmp_path / "editorial" / "analises" / "relatorios" / "2026-09-23" / "diagnostico.json"
    d = json.loads(destino.read_text())
    assert d["retrato"] == "editorial/analises/dados/youtube/2026-09-23T0401_30d.json"
    assert por_id(d["kpis"])["views"]["valor"] == 2222
    assert set(d) >= {"gerado_em", "coletado_em", "canal", "kpis", "videos", "formatos", "trafego", "tendencia"}


def test_main_com_retrato_do_coletor(tmp_path):
    falso = YouTubeFalso(ultimo_dia="2026-09-20")
    cy.main([], cliente=falso.cliente(tmp_path), raiz=tmp_path, hoje="2026-09-23")
    d = json.loads(dg.main([], raiz=tmp_path, hoje="2026-09-23").read_text())
    views = [f["views"] for f in d["videos"]]
    assert views == sorted(views, reverse=True) and len(views) == 12
    assert d["formatos"]["7d"][0]["tipo"] == "VIDEO_ON_DEMAND"
    assert d["tendencia"][-1]["dia"] == "2026-09-20" and d["tendencia"][-1]["views"] == 100


def test_main_sem_retrato_explica(tmp_path):
    with pytest.raises(SystemExit, match="nenhum retrato"):
        dg.main([], raiz=tmp_path, hoje="2026-09-23")


LEITURA = {
    "tese": "Shorts trouxeram os inscritos da semana.",
    "subtese": "Vídeos longos seguraram o tempo assistido.",
    "kpis": ["Views subiram 10%."],
    "achados": [{"titulo": "Shorts convertem", "achado": "3 de 5 inscritos vieram de Shorts", "evidencia": "diagnostico.json formatos.7d", "muda": "mais um Short por semana"}],
    "acoes": [["Publicar Short na quarta", "melhor dia medido"]],
    "limites": ["Amostra de uma semana."],
    "cerebro": {"confirma": [], "questiona": []},
}


def _pasta_com(tmp_path, leitura):
    pasta = tmp_path / "rel"
    pasta.mkdir()
    (pasta / "leitura.json").write_text(json.dumps(leitura, ensure_ascii=False))
    return pasta


def test_validar_leitura_completa_sai_zero(tmp_path, capsys):
    pasta = _pasta_com(tmp_path, LEITURA)
    assert dg.validar_leitura(pasta) == []
    assert dg.validar_leitura_cli(["--pasta", str(pasta)]) == 0


@pytest.mark.parametrize("estraga, esperado", [
    (lambda l: l.pop("tese"), "tese"),
    (lambda l: l["achados"][0].update(evidencia=""), "achados[0].evidencia"),
    (lambda l: l.update(acoes=[["só a ação"]]), "acoes[0]"),
])
def test_validar_leitura_aponta_a_falta(tmp_path, capsys, estraga, esperado):
    leitura = copy.deepcopy(LEITURA)
    estraga(leitura)
    pasta = _pasta_com(tmp_path, leitura)
    assert any(esperado in e for e in dg.validar_leitura(pasta))
    assert dg.validar_leitura_cli(["--pasta", str(pasta)]) == 1
    assert esperado in capsys.readouterr().out


def test_validar_leitura_sem_arquivo(tmp_path):
    assert dg.validar_leitura(tmp_path) == ["leitura.json ausente ou inválido"]
