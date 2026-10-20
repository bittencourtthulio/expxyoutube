"""Diário de decisões da rotina e do chat."""
import json

import pytest

import decisoes

ARGS = ["registrar", "--tipo", "pauta", "--o-que", "Priorizar Shorts", "--por-que", "Shorts trouxeram 60% dos inscritos",
        "--evidencia", "relatorios/2026-09-23/diagnostico.json", "--como-desfazer", "voltar a 1 Short por semana"]


@pytest.fixture(autouse=True)
def raiz(tmp_path, monkeypatch):
    monkeypatch.setattr(decisoes, "RAIZ", tmp_path)
    return tmp_path


def test_registrar_grava_os_seis_campos(raiz):
    assert decisoes.main(ARGS) == 0
    [linha] = (raiz / "estado" / "decisoes.jsonl").read_text().splitlines()
    d = json.loads(linha)
    assert set(d) >= {"quando", "tipo", "o_que", "por_que", "evidencia", "como_desfazer"}
    assert d["o_que"] == "Priorizar Shorts" and d["autor"] == "rotina"


def test_registrar_sem_por_que_sai_1(raiz, capsys):
    args = [a for a in ARGS]
    i = args.index("--por-que")
    del args[i:i + 2]
    assert decisoes.main(args) == 1
    assert "por_que" in capsys.readouterr().err
    assert not (raiz / "estado" / "decisoes.jsonl").exists()


def test_lista_da_mais_nova_para_a_mais_antiga(capsys):
    decisoes.main(ARGS)
    decisoes.main(ARGS[:4] + ["Segunda"] + ARGS[5:] + ["--autor", "analista", "--daily", "d003"])
    capsys.readouterr()
    assert decisoes.main(["lista", "--json"]) == 0
    lista = json.loads(capsys.readouterr().out)
    assert [d["o_que"] for d in lista] == ["Segunda", "Priorizar Shorts"]
    assert lista[0]["autor"] == "analista" and lista[0]["daily"] == "d003"
