"""Coletor: janelas ancoradas no último dia com dado, totais agregados, séries, tráfego, formatos e top."""
import pytest

import coletar_youtube as cy
from tests.falsos import YouTubeFalso


def test_janelas_ancoradas_no_ultimo_dia_com_dado(tmp_path):
    c = YouTubeFalso(ultimo_dia="2026-09-20").cliente(tmp_path)
    j = cy.janelas(c, hoje="2026-09-23")
    assert j["ultimo_dia"] == "2026-09-20"
    assert j["7d"] == {"desde": "2026-09-14", "ate": "2026-09-21"}
    assert j["7d_anteriores"] == {"desde": "2026-09-07", "ate": "2026-09-14"}
    assert j["30d"] == {"desde": "2026-08-22", "ate": "2026-09-21"}
    assert j["28d"] == {"desde": "2026-08-24", "ate": "2026-09-21"}


def test_sem_nenhum_dia_com_dado_explica(tmp_path):
    c = YouTubeFalso(ultimo_dia="2026-01-01", primeiro_dia="2026-01-01").cliente(tmp_path)
    with pytest.raises(cy.SemDados, match="nenhum dia"):
        cy.janelas(c, hoje="2026-09-23")


def test_totais_por_janela_pedidos_agregados(tmp_path):
    falso = YouTubeFalso(ultimo_dia="2026-09-20")
    c = falso.cliente(tmp_path)
    j = cy.janelas(c, hoje="2026-09-23")
    r = cy.coletar_canal(c, j)
    v7 = r["janelas"]["7d"]["valores"]
    assert v7["views"] == 700 and v7["subscribersGained"] == 21 and v7["averageViewDuration"] == 150
    assert r["janelas"]["7d_anteriores"]["valores"]["views"] == 700
    assert r["janelas"]["30d"]["valores"]["views"] == 3000
    assert r["janelas"]["7d"]["desde"] == "2026-09-14" and r["janelas"]["7d"]["recusadas"] == []
    # a API recebe endDate inclusivo = ate - 1 dia
    totais = [p for p in falso.pedidos if not p["dimensions"] and p["startDate"] == "2026-09-14"]
    assert totais and totais[0]["endDate"] == "2026-09-20"


def test_series_diarias_com_nomes_do_harness(tmp_path):
    c = YouTubeFalso(ultimo_dia="2026-09-20").cliente(tmp_path)
    r = cy.coletar_canal(c, cy.janelas(c, hoje="2026-09-23"))
    views = r["series"]["views"]
    assert views[-1] == {"dia": "2026-09-20", "valor": 100}
    assert len(views) == 60
    assert r["series"]["inscritos_ganhos"][0]["valor"] == 3
    assert set(r["series"]) >= {"views", "inscritos_ganhos", "inscritos_perdidos", "minutos"}


def test_metrica_recusada_nao_derruba_as_outras(tmp_path):
    c = YouTubeFalso(ultimo_dia="2026-09-20", recusar={"engagedViews"}).cliente(tmp_path)
    r = cy.coletar_canal(c, cy.janelas(c, hoje="2026-09-23"))
    j7 = r["janelas"]["7d"]
    assert "engagedViews" not in j7["valores"] and j7["valores"]["views"] == 700
    assert [x["metrica"] for x in j7["recusadas"]] == ["engagedViews"]
    assert "engaged_views" not in r["series"] and r["series"]["views"]


def _retrato(tmp_path, **kw):
    falso = YouTubeFalso(ultimo_dia="2026-09-20", **kw)
    arq = cy.main([], cliente=falso.cliente(tmp_path), raiz=tmp_path, hoje="2026-09-23")
    return falso, arq, cy.comum.ler_json(arq)


def test_main_grava_retrato_na_pasta_de_dados(tmp_path):
    _, arq, r = _retrato(tmp_path)
    assert arq.parent == tmp_path / "editorial" / "analises" / "dados" / "youtube"
    assert arq.name.endswith("_30d.json")
    assert set(r) >= {"coletado_em", "periodo_dias", "canal", "janelas", "series", "trafego", "formatos", "top_videos", "videos"}
    assert r["canal"]["id"] == "UCfalso" and r["canal"]["inscritos"] == 9630


def test_top_videos_ordenados_com_titulo_e_link_por_formato(tmp_path):
    _, _, r = _retrato(tmp_path)
    top = r["top_videos"]
    assert len(top) == 12
    assert [v["views"] for v in top] == sorted((v["views"] for v in top), reverse=True)
    v1 = next(v for v in top if v["id"] == "v01")
    assert v1["titulo"] == "Vídeo 01" and v1["publicado_em"] == "2026-09-13" and v1["formato"] == "VIDEO_ON_DEMAND"
    assert v1["link"] == "https://www.youtube.com/watch?v=v01"
    v2 = next(v for v in top if v["id"] == "v02")
    assert v2["formato"] == "SHORTS" and v2["link"] == "https://www.youtube.com/shorts/v02"


def test_trafego_e_formatos_por_janela(tmp_path):
    _, _, r = _retrato(tmp_path)
    t7 = {t["tipo"]: t["views"] for t in r["trafego"]["7d"]}
    assert t7["YT_SEARCH"] == 210 and sum(t7.values()) == 700
    f7 = {f["tipo"]: f["views"] for f in r["formatos"]["7d"]}
    assert f7 == {"SHORTS": 210, "VIDEO_ON_DEMAND": 490}
    assert "7d_anteriores" in r["trafego"] and "28d" in r["formatos"]


def test_uploads_recentes_com_estatisticas_publicas(tmp_path):
    _, _, r = _retrato(tmp_path)
    v = r["videos"][0]
    assert v["id"] == "v01" and v["views_total"] == 5000 and v["duracao_seg"] == 540
    assert r["canal"]["publicacoes"] == {"7d": 0, "7d_anteriores": 2}


def test_formato_do_video_pela_duracao_quando_a_api_recusa(tmp_path):
    _, _, r = _retrato(tmp_path, recusar_video_formato=True)
    por_id = {v["id"]: v for v in r["top_videos"]}
    assert por_id["v02"]["formato"] == "SHORTS" and por_id["v02"]["formato_por"] == "duracao"
    assert por_id["v01"]["formato"] == "VIDEO_ON_DEMAND" and por_id["v02"]["link"].endswith("/shorts/v02")
    assert r["formatos"]["7d"]  # o cartão Shorts x vídeos continua vindo da Analytics


def test_formato_em_camelcase_da_api_real_e_normalizado():
    assert cy.normaliza_formato("videoOnDemand") == "VIDEO_ON_DEMAND"
    assert cy.normaliza_formato("shorts") == "SHORTS"
    assert cy.normaliza_formato("liveStream") == "LIVE_STREAM"
    assert cy.normaliza_formato("creatorContentTypeUnspecified") == "UNSPECIFIED"
    assert cy.normaliza_formato("SHORTS") == "SHORTS"
    assert cy.normaliza_formato("algoNovo") == "ALGO_NOVO"
