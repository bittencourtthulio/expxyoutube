"""Plano do dia determinístico: análise base, KPIs, pendentes, regras e pautas da biblioteca."""
import json

import pytest

import daily
import planejar

NOTA = '''---
id: "abc"
titulo: "IA para software house"
canal: "canal-x"
publicado_em: "{data}"
status: "{status}"
relevancia: "{rel}"
temas: ["agentes"]
---
# IA para software house

## Resumo
Resumo.

## Ideias de conteúdo
- **Agentes que fazem code review.** O ângulo: mostrar o fluxo. Cabe em: video-longo. [agentes] [03:10]
- **Três prompts para PR.** O ângulo: short. Cabe em: short. [prompts] [05:00]

## Ressalvas
Nenhuma.
'''


@pytest.fixture
def raiz(tmp_path, monkeypatch):
    monkeypatch.setattr(planejar, "RAIZ", tmp_path)
    monkeypatch.setattr(daily, "RAIZ", tmp_path)
    diag = {"kpis": {"janela": {"desde": "2026-09-14", "ate": "2026-09-21"}, "basicas": [
        {"id": "views", "nome": "Views", "valor": 1100, "anterior": 1000, "variacao_pct": 10.0, "unidade": ""},
        {"id": "inscritos_ganhos", "nome": "Inscritos ganhos", "valor": 30, "anterior": 20, "variacao_pct": 50.0, "unidade": ""}],
        "performance": [{"id": "taxa_engajamento", "nome": "Engajamento por view", "valor": 7.3, "anterior": 7.0, "variacao_pct": 4.3, "unidade": "%"}]}}
    pasta = tmp_path / "editorial" / "analises" / "relatorios" / "2026-09-22"
    pasta.mkdir(parents=True)
    (pasta / "diagnostico.json").write_text(json.dumps(diag))
    (pasta / "leitura.json").write_text(json.dumps({"tese": "Shorts puxaram a semana."}))
    vids = tmp_path / "biblioteca" / "videos" / "canal-x"
    vids.mkdir(parents=True)
    (vids / "a.md").write_text(NOTA.format(data="2026-09-20", status="destilado", rel="alta"))
    (vids / "b.md").write_text(NOTA.format(data="2026-09-21", status="bruto", rel="alta").replace("abc", "bruta"))
    (vids / "c.md").write_text(NOTA.format(data="2026-09-19", status="destilado", rel="fora").replace("abc", "fora"))
    daily.novo("tarefa", "Compare Shorts e vídeos longos", para="analista")
    daily.novo("nao-fazer", "Não use clickbait")
    return tmp_path


def test_criar_monta_o_plano(raiz, capsys):
    assert planejar.main(["criar", "--data", "2026-09-23", "--json"]) == 0
    plano = json.loads((raiz / "planejamento" / "2026-09-23.json").read_text())
    assert plano["analise_base"] == "editorial/analises/relatorios/2026-09-22"
    assert plano["tese"] == "Shorts puxaram a semana."
    k = {x["id"]: x for x in plano["kpis"]}
    assert k["views"]["valor"] == 1100 and k["views"]["variacao_pct"] == 10.0 and "taxa_engajamento" in k
    assert [p["id"] for p in plano["pendentes"]] == ["d001", "d002"]  # regra nova fica pendente até ser aplicada
    assert [r["id"] for r in plano["regras"]] == ["d002"]
    assert [p["titulo"] for p in plano["pautas"]] == ["Agentes que fazem code review.", "Três prompts para PR."]
    assert plano["pautas"][0]["cabe_em"] == "video-longo" and plano["pautas"][1]["cabe_em"] == "short"
    assert plano["pautas"][0]["fonte"].startswith("biblioteca/videos/canal-x/a.md")
    assert plano["notas_do_planejador"] == []


def test_criar_repetido_sem_refazer_sai_1_e_nota_acrescenta(raiz, capsys):
    assert planejar.main(["criar", "--data", "2026-09-23"]) == 0
    assert planejar.main(["criar", "--data", "2026-09-23"]) == 1
    assert "--refazer" in capsys.readouterr().err
    assert planejar.main(["nota", "--data", "2026-09-23", "--texto", "Priorizar o Short de quarta"]) == 0
    plano = json.loads((raiz / "planejamento" / "2026-09-23.json").read_text())
    assert [n["texto"] for n in plano["notas_do_planejador"]] == ["Priorizar o Short de quarta"]
    assert planejar.main(["criar", "--data", "2026-09-23", "--refazer"]) == 0
    plano = json.loads((raiz / "planejamento" / "2026-09-23.json").read_text())
    assert [n["texto"] for n in plano["notas_do_planejador"]] == ["Priorizar o Short de quarta"]


def test_sem_analise_o_plano_diz_que_nao_tem(tmp_path, monkeypatch):
    monkeypatch.setattr(planejar, "RAIZ", tmp_path)
    monkeypatch.setattr(daily, "RAIZ", tmp_path)
    plano = planejar.criar("2026-09-23")
    assert plano["analise_base"] is None and plano["kpis"] == [] and plano["pautas"] == []
