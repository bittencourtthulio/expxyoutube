"""O falso da API responde como a Analytics/Data API para os testes dos módulos."""
import pytest

import yt
from tests.falsos import YouTubeFalso


@pytest.fixture
def falso():
    return YouTubeFalso(ultimo_dia="2026-09-20")


def test_consulta_por_dia_devolve_uma_linha_por_dia_ate_o_ultimo_com_dado(falso, tmp_path):
    c = falso.cliente(tmp_path)
    linhas = c.relatorio("2026-09-10", "2026-09-23", ["views", "subscribersGained"], dimensoes=["day"], sort="day")
    assert [l["day"] for l in linhas] == [f"2026-09-{d:02d}" for d in range(10, 21)]
    assert all(l["views"] == 100 and l["subscribersGained"] == 3 for l in linhas)


def test_consulta_sem_dimensao_soma_as_contagens(falso, tmp_path):
    [total] = falso.cliente(tmp_path).relatorio("2026-09-14", "2026-09-20", ["views", "likes", "averageViewDuration"])
    assert total["views"] == 700 and total["likes"] == 35
    assert total["averageViewDuration"] == 150


def test_periodo_sem_dado_nao_tem_rows(falso, tmp_path):
    assert falso.cliente(tmp_path).relatorio("2026-09-21", "2026-09-23", ["views"]) == []


def test_top_videos_ordenado_e_limitado(falso, tmp_path):
    linhas = falso.cliente(tmp_path).relatorio("2026-08-24", "2026-09-20", ["views", "likes"], dimensoes=["video"], sort="-views", max_results=10)
    assert len(linhas) == 10
    views = [l["views"] for l in linhas]
    assert views == sorted(views, reverse=True)


def test_trafego_e_formato(falso, tmp_path):
    c = falso.cliente(tmp_path)
    trafego = c.relatorio("2026-09-14", "2026-09-20", ["views", "estimatedMinutesWatched"], dimensoes=["insightTrafficSourceType"])
    assert {l["insightTrafficSourceType"] for l in trafego} >= {"YT_SEARCH", "RELATED_VIDEO", "BROWSE_NOVO"}
    assert sum(l["views"] for l in trafego) == 700
    formatos = c.relatorio("2026-09-14", "2026-09-20", ["views"], dimensoes=["creatorContentType"])
    assert {l["creatorContentType"]: l["views"] for l in formatos} == {"SHORTS": 210, "VIDEO_ON_DEMAND": 490}


def test_metrica_recusada_da_400(tmp_path):
    f = YouTubeFalso(recusar={"engagedViews"})
    with pytest.raises(yt.ErroAPI) as e:
        f.cliente(tmp_path).relatorio("2026-09-14", "2026-09-20", ["views", "engagedViews"])
    assert e.value.status == 400


def test_data_api(falso, tmp_path):
    c = falso.cliente(tmp_path)
    canal = c.canal()
    assert canal["id"] == "UCfalso" and canal["statistics"]["subscriberCount"] == "9630"
    assert [v["id"] for v in c.videos(["v01", "v02"])] == ["v01", "v02"]
    assert c.videos(["v01"])[0]["snippet"]["title"] == "Vídeo 01"
    assert len(c.uploads(canal["contentDetails"]["relatedPlaylists"]["uploads"], limite=5)) == 5
