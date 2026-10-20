"""Daily: fios do Usuário com a equipe, derivados de um log só por acréscimo."""
import json

import pytest

import daily


@pytest.fixture(autouse=True)
def raiz(tmp_path, monkeypatch):
    monkeypatch.setattr(daily, "RAIZ", tmp_path)
    return tmp_path


def test_ids_em_sequencia_e_estado_inicial():
    a = daily.novo("tarefa", "Analise a queda de views")
    b = daily.novo("nao-fazer", "Não use clickbait no título", para="roteirista")
    assert (a["id"], b["id"]) == ("d001", "d002")
    fios = {f["id"]: f for f in daily.itens()}
    assert fios["d001"]["status"] == "aberta" and fios["d001"]["situacao"] == "pendente"
    assert fios["d002"]["status"] == "ativa" and fios["d002"]["regra_em_vigor"]


def test_destinatario_e_tipo_invalidos():
    with pytest.raises(daily.Erro, match="destinatário"):
        daily.novo("tarefa", "x", para="copywriter")
    with pytest.raises(daily.Erro, match="tipo"):
        daily.novo("ordem", "x")
    with pytest.raises(daily.Erro, match="texto"):
        daily.novo("tarefa", "   ")
    assert set(daily.PARA) == {"planejador", "analista", "roteirista", "curador", "bibliotecario", "reviewer", "apresentador", "validador", "ambos", "todos"}


def test_resposta_da_rotina_e_status_permitido():
    daily.novo("tarefa", "Faça X")
    daily.responder("d001", "Comecei", autor="analista", status="fazendo")
    f = daily.item("d001")
    assert f["status"] == "fazendo" and f["situacao"] == "executando"
    with pytest.raises(daily.Erro, match="não vale"):
        daily.responder("d001", "x", autor="analista", status="cancelada")


def test_regra_em_vigor_antes_e_depois_de_aplicada_e_por_serie():
    daily.novo("nao-fazer", "Nada de GLM", serie="shorts")
    daily.novo("aprendizado", "Títulos com número funcionam")
    assert [f["id"] for f in daily.regras()] == ["d001", "d002"]
    daily.responder("d001", "Aplicado", autor="planejador", status="aplicada", onde="editorial/voz.md")
    assert [f["id"] for f in daily.regras("shorts")] == ["d001", "d002"]
    assert [f["id"] for f in daily.regras("video-longo")] == ["d002"]
    daily.encerrar("d001", "mudei de ideia")
    assert [f["id"] for f in daily.regras()] == ["d002"]


def test_replica_do_usuario_reabre_para_a_rotina():
    daily.novo("pergunta", "Por que caiu?")
    daily.responder("d001", "Caiu por causa do feriado. Quer que eu compare com o ano passado?", autor="analista")
    assert daily.item("d001")["aguarda_usuario"]
    assert not daily.pendentes()
    daily.responder("d001", "Sim, compare", autor=daily.USUARIO)
    assert [f["id"] for f in daily.pendentes()] == ["d001"]


def test_mover_e_editar_com_revisao():
    daily.novo("tarefa", "Faça Y")
    f = daily.item("d001")
    daily.mover("d001", "executando", revisao=f["revisao"])
    with pytest.raises(daily.Erro, match="mudou"):
        daily.editar("d001", "Título", "Texto", revisao=0)
    daily.editar("d001", "Título", "Texto novo", revisao=1)
    assert daily.item("d001")["texto"] == "Texto novo" and daily.item("d001")["situacao"] == "executando"


def test_log_so_cresce(raiz):
    daily.novo("tarefa", "a")
    daily.responder("d001", "b", autor="analista")
    daily.finalizar("d001")
    linhas = (raiz / "estado" / "daily.jsonl").read_text().splitlines()
    assert [json.loads(l)["evento"] for l in linhas] == ["novo", "resposta", "mover"]
    with pytest.raises(daily.Erro, match="já está"):
        daily.finalizar("d001")


def test_linha_corrompida_e_pulada_e_contada(raiz, capsys):
    daily.novo("tarefa", "a")
    with (raiz / "estado" / "daily.jsonl").open("a") as f:
        f.write("{linha quebrada\n")
    daily.novo("tarefa", "b")
    assert [f["id"] for f in daily.itens()] == ["d002", "d001"]
    assert daily.main(["saude", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"eventos": 2, "corrompidas": 1}


def test_revisar_nao_encerra_por_calendario():
    daily.novo("tarefa", "Com prazo")
    daily.editar("d001", "Com prazo", "Com prazo", data_final="2026-09-20")
    r = daily.revisar("2026-09-23")
    assert [f["id"] for f in r["verificar_conclusao"]] == ["d001"]
    assert daily.item("d001")["status"] == "aberta"


def _grava(raiz, rel, dados):
    p = raiz / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dados, ensure_ascii=False))


KPIS = {"janela": {"desde": "2026-09-14", "ate": "2026-09-21"}, "basicas": [{"id": "views", "nome": "Views", "valor": 10, "anterior": 5}],
        "performance": [], "series": {}}


def test_kpis_pega_a_analise_mais_recente_que_tem_kpis(raiz):
    _grava(raiz, "editorial/analises/relatorios/2026-09-21/diagnostico.json", {"kpis": KPIS, "canal": {"titulo": "C"}, "coletado_em": "x"})
    _grava(raiz, "editorial/analises/relatorios/2026-09-21/leitura.json", {"kpis": ["Views dobraram."], "tese": "Semana boa."})
    _grava(raiz, "editorial/analises/relatorios/2026-09-22/diagnostico.json", {"kpis": None})
    k = daily.kpis()
    assert k["data"] == "2026-09-21" and k["canal"]["titulo"] == "C"
    assert k["leitura"] == ["Views dobraram."] and k["tese"] == "Semana boa."
    assert set(k["dashboard"]) == {"semanas", "interacoes", "trafego", "formatos", "top_videos"}


def test_kpis_sem_analise_devolve_none():
    assert daily.kpis() is None


def test_dias_e_ata_do_dia(raiz):
    _grava(raiz, "planejamento/2026-09-23.json", {"data": "2026-09-23", "gerado_em": "2026-09-23T06:00:00-03:00",
                                                  "analise_base": "editorial/analises/relatorios/2026-09-23"})
    _grava(raiz, "editorial/analises/relatorios/2026-09-23/diagnostico.json", {"kpis": KPIS, "canal": {"titulo": "C"},
                                                                               "videos": [{"id": f"v{i}"} for i in range(8)]})
    _grava(raiz, "editorial/analises/relatorios/2026-09-23/leitura.json", {"tese": "T"})
    (raiz / "estado").mkdir(exist_ok=True)
    (raiz / "estado" / "decisoes.jsonl").write_text(json.dumps({"quando": "2026-09-23T07:00:00-03:00", "o_que": "x"}) + "\n")
    d = [x for x in daily.dias() if x["data"] == "2026-09-23"][0]
    assert d["plano"] and d["analise"] and d["decisoes"] == 1
    ata = daily.montar_dia("2026-09-23")
    assert ata["plano"]["data"] == "2026-09-23"
    assert ata["analise"]["leitura"]["tese"] == "T" and len(ata["analise"]["videos"]) == 5
    assert [x["o_que"] for x in ata["decisoes"]] == ["x"]


def test_kpis_com_duas_analises_validas_usa_a_mais_nova(raiz):
    _grava(raiz, "editorial/analises/relatorios/2026-09-20/diagnostico.json", {"kpis": KPIS, "canal": {"titulo": "velho"}})
    _grava(raiz, "editorial/analises/relatorios/2026-09-21/diagnostico.json", {"kpis": KPIS, "canal": {"titulo": "novo"}})
    assert daily.kpis()["canal"]["titulo"] == "novo"
