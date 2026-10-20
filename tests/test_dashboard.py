"""Recortes do painel: semanas somadas sem inventar dia, interações, tráfego, formatos e top."""
from datetime import date, timedelta

import dashboard


def dados():
    fim = date(2026, 9, 21)
    pontos = [{"dia": (fim - timedelta(days=28 - i)).isoformat(), "valor": 100} for i in range(28)]
    kpi = lambda i, n, a, b: {"id": i, "nome": n, "valor": a, "anterior": b}
    return {
        "kpis": {"janela": {"desde": "2026-09-14", "ate": "2026-09-21"}, "comparado_com": {"desde": "2026-09-07", "ate": "2026-09-14"},
                 "series": {"views": pontos, "inscritos_ganhos": [{**p, "valor": 2} for p in pontos]},
                 "basicas": [kpi("curtidas", "Curtidas", 50, 40), kpi("comentarios", "Comentários", 0, 3),
                             kpi("compartilhamentos", "Compartilhamentos", None, 2), kpi("inscritos_ganhos", "Inscritos ganhos", 30, 20),
                             kpi("inscritos_perdidos", "Inscrições canceladas", 5, 4)],
                 "performance": []},
        "trafego": {"7d": [{"tipo": "YT_SEARCH", "views": 300}, {"tipo": "RELATED_VIDEO", "views": 500}, {"tipo": "ALGO_NOVO", "views": 10}],
                    "7d_anteriores": [{"tipo": "YT_SEARCH", "views": 200}]},
        "formatos": {"7d": [{"tipo": "SHORTS", "views": 210, "minutos": 100, "taxa_engajamento": 3.0, "inscritos": 9},
                            {"tipo": "VIDEO_ON_DEMAND", "views": 490, "minutos": 900, "taxa_engajamento": 2.0, "inscritos": 12}],
                     "7d_anteriores": [{"tipo": "SHORTS", "views": 100}]},
        "videos": [{"id": f"v{i}", "titulo": f"V{i}", "link": f"https://www.youtube.com/watch?v=v{i}", "views": 100 - i, "nota": 5}
                   for i in range(12)] + [{"id": "mal", "titulo": "x", "link": "javascript:alert(1)", "views": 1}],
    }


def test_semanas_somam_views_e_sao_contiguas():
    s = dashboard.montar(dados())["semanas"]
    assert len(s) == 4
    assert [(x["views"], x["inscritos_ganhos"]) for x in s] == [(700, 14)] * 4
    assert all(s[i]["ate"] == s[i + 1]["desde"] for i in range(3))
    assert s[-1]["desde"] == "2026-09-14" and s[-1]["ate"] == "2026-09-21"


def test_dia_ausente_deixa_semana_sem_valor_e_zero_real_conta():
    d = dados()
    d["kpis"]["series"]["views"].pop()
    d["kpis"]["series"]["inscritos_ganhos"][-7:] = [{**p, "valor": 0} for p in d["kpis"]["series"]["inscritos_ganhos"][-7:]]
    s = dashboard.montar(d)["semanas"][-1]
    assert s["views"] is None and s["views_dias"] == 6
    assert s["inscritos_ganhos"] == 0 and s["inscritos_ganhos_dias"] == 7


def test_interacoes_atual_e_anterior_dos_kpis():
    i = {x["id"]: x for x in dashboard.montar(dados())["interacoes"]}
    assert i["curtidas"]["atual"] == 50 and i["curtidas"]["anterior"] == 40
    assert i["comentarios"]["atual"] == 0
    assert i["compartilhamentos"]["atual"] is None
    assert i["inscritos_ganhos"]["nome"] == "Inscritos ganhos"


def test_trafego_ordenado_com_rotulo_e_fallback():
    t = dashboard.montar(dados())["trafego"]
    assert [x["tipo"] for x in t] == ["RELATED_VIDEO", "YT_SEARCH", "ALGO_NOVO"]
    assert t[0]["rotulo"] == "Vídeos sugeridos" and t[1]["rotulo"] == "Busca do YouTube"
    assert t[1]["anterior"] == 200 and t[0]["anterior"] is None
    assert t[2]["rotulo"] == "Outra origem (ALGO_NOVO)"


def test_formatos_com_rotulo_e_anterior():
    f = {x["tipo"]: x for x in dashboard.montar(dados())["formatos"]}
    assert f["SHORTS"]["rotulo"] == "Shorts" and f["SHORTS"]["views_anterior"] == 100
    assert f["VIDEO_ON_DEMAND"]["rotulo"] == "Vídeos" and f["VIDEO_ON_DEMAND"]["views_anterior"] is None


def test_top_dez_so_com_link_do_youtube():
    top = dashboard.montar(dados())["top_videos"]
    assert len(top) == 10 and top[0]["id"] == "v0"
    d = dados()
    d["videos"] = d["videos"][-1:]
    assert dashboard.montar(d)["top_videos"][0]["link"] is None


def test_diagnostico_vazio_nao_quebra():
    r = dashboard.montar({})
    assert r == {"semanas": [], "interacoes": [], "trafego": [], "formatos": [], "top_videos": []}
