"""Utilitários de arquivo, número e fuso compartilhados por todos os módulos."""
import json
import math
from datetime import datetime

import comum


def test_gravar_atomico_e_ler_json(tmp_path):
    alvo = tmp_path / "a" / "b.json"
    comum.gravar_json(alvo, {"x": 1, "ç": "ã"})
    assert comum.ler_json(alvo) == {"x": 1, "ç": "ã"}
    assert not list(alvo.parent.glob("*.tmp"))


def test_ler_json_ausente_ou_quebrado_devolve_padrao(tmp_path):
    assert comum.ler_json(tmp_path / "nao.json", {"p": 1}) == {"p": 1}
    (tmp_path / "q.json").write_text("{quebrado")
    assert comum.ler_json(tmp_path / "q.json", []) == []


def test_jsonl_anexa_e_le_na_ordem(tmp_path):
    arq = tmp_path / "estado" / "log.jsonl"
    comum.anexar_jsonl(arq, {"n": 1})
    comum.anexar_jsonl(arq, {"n": 2})
    eventos, corrompidas = comum.ler_jsonl(arq)
    assert [e["n"] for e in eventos] == [1, 2]
    assert corrompidas == 0


def test_jsonl_com_linha_corrompida_pula_e_conta(tmp_path):
    arq = tmp_path / "log.jsonl"
    arq.write_text(json.dumps({"n": 1}) + "\n{meia linha\n" + json.dumps({"n": 3}) + "\n\n")
    eventos, corrompidas = comum.ler_jsonl(arq)
    assert [e["n"] for e in eventos] == [1, 3]
    assert corrompidas == 1


def test_jsonl_ausente(tmp_path):
    assert comum.ler_jsonl(tmp_path / "x.jsonl") == ([], 0)


def test_numero():
    assert comum.numero(3) and comum.numero(0) and comum.numero(2.5)
    assert not comum.numero(True)
    assert not comum.numero(-5)
    assert not comum.numero(math.nan) and not comum.numero(math.inf)
    assert not comum.numero("3") and not comum.numero(None)
    assert comum.numero(-5, sinal=True)
    assert comum.valor(-5) is None and comum.valor(-5, sinal=True) == -5


def test_fusos():
    assert comum.SP.key == "America/Sao_Paulo"
    assert comum.PACIFICO.key == "America/Los_Angeles"
    # 02:00 UTC de 24/09 ainda é 23/09 em São Paulo e 23/09 no Pacífico
    instante = datetime(2026, 9, 24, 2, 0, tzinfo=comum.UTC)
    assert comum.hoje_sp(instante) == "2026-09-23"
    assert comum.hoje_pacifico(instante) == "2026-09-23"
    assert comum.agora_iso().endswith(("-03:00", "-02:00"))
