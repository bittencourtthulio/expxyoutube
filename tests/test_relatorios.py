"""Central de relatórios do canal: catálogo, projeção de colunas, zero preservado e data validada."""
import json

import pytest

import coletar_youtube as cy
import daily
import decisoes
import diagnostico as dg
import relatorios
from tests.falsos import YouTubeFalso


@pytest.fixture
def raiz(tmp_path, monkeypatch):
    for mod in (daily, decisoes):
        monkeypatch.setattr(mod, "RAIZ", tmp_path)
    cy.main([], cliente=YouTubeFalso(ultimo_dia="2026-09-20").cliente(tmp_path), raiz=tmp_path, hoje="2026-09-23")
    destino = dg.main([], raiz=tmp_path, hoje="2026-09-23")
    diag = json.loads(destino.read_text())
    diag["videos"][0]["comentarios"] = 0
    diag["videos"][1]["comentarios"] = None
    destino.write_text(json.dumps(diag))
    (destino.parent / "leitura.json").write_text(json.dumps({"tese": "T", "achados": [{"titulo": "A", "achado": "B", "evidencia": "C", "muda": "D"}],
                                                             "acoes": [["Fazer", "porque"]], "limites": ["L"], "kpis": ["K"]}))
    decisoes.registrar("pauta", "Priorizar Shorts", "dados", "diag", "voltar")
    daily.novo("tarefa", "Compare formatos", para="analista")
    return tmp_path


def test_catalogo_com_fontes_e_linhas(raiz):
    r = relatorios.montar(raiz, fios=daily.itens())
    ids = [x["id"] for x in r["relatorios"]]
    assert len(ids) >= 25 and len(set(ids)) == len(ids)
    assert all(x["fontes"] for x in r["relatorios"])
    com_linhas = [x["id"] for x in r["relatorios"] if x["linhas"]]
    assert len(com_linhas) >= 15, com_linhas
    assert r["data"] == "2026-09-23" and r["datas"] == ["2026-09-23"]


def test_projecao_nao_vaza_campos_fora_das_colunas(raiz):
    for rel in relatorios.montar(raiz)["relatorios"]:
        chaves = {c["key"] for c in rel["colunas"]}
        assert all(set(l) <= chaves for l in rel["linhas"]), rel["id"]


def test_zero_preservado_e_ausencia_fora_do_ranking(raiz):
    rel = {x["id"]: x for x in relatorios.montar(raiz)["relatorios"]}["ranking-comentarios"]
    valores = [l["comentarios"] for l in rel["linhas"]]
    assert 0 in valores and None not in valores
    assert valores == sorted(valores, reverse=True)


def test_data_invalida_e_base_vazia(raiz, tmp_path_factory):
    with pytest.raises(ValueError):
        relatorios.montar(raiz, data="../../.env")
    vazio = relatorios.montar(tmp_path_factory.mktemp("vazio"))
    assert vazio["relatorios"] and all(x["linhas"] == [] or x["escopo"] == "atual" for x in vazio["relatorios"])


def test_arquivo_quebrado_vira_aviso(raiz):
    (raiz / "estado" / "decisoes.jsonl").write_text("{quebrado\n")
    r = relatorios.montar(raiz)
    assert any("decisoes.jsonl" in a for a in r["avisos"])
