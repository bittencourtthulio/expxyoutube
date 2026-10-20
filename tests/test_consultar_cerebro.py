"""consultar_cerebro: práticas por tema para a análise e o plano, só do que foi destilado e serve."""
import json
from pathlib import Path

import pytest

import cerebro
import consultar_cerebro as cc

RAIZ_REAL = Path(__file__).resolve().parents[1]


@pytest.fixture
def base(tmp_path, monkeypatch):
    for nome, valor in {**cerebro.globais_da_base(cerebro.BASE, tmp_path), "RAIZ": tmp_path}.items():
        monkeypatch.setattr(cerebro, nome, valor)
    cerebro.gravar_json(cerebro.TEMAS, {"temas": [{"id": "miniatura", "nome": "Miniatura"}, {"id": "retencao", "nome": "Retenção"}]})
    pasta = cerebro.VIDEOS / "canal-x"
    pasta.mkdir(parents=True)

    def nota(vid, dia, relevancia, temas, praticas):
        (pasta / f"{dia}-{vid}.md").write_text(
            f'---\nid: "{vid}"\ntitulo: "Vídeo {vid}"\ncanal: "canal-x"\ncanal_nome: "Canal X"\nurl: "https://www.youtube.com/watch?v={vid}"\n'
            f'publicado_em: "{dia}"\ningerido_em: "{dia}"\nduracao_seg: 600\nidioma: "en"\nlegenda: "manual"\nvisualizacoes: 10\n'
            f'transcricao_sha: "x"\nstatus: "destilado"\nrelevancia: "{relevancia}"\ntemas: {json.dumps(temas)}\ndestilado_em: "{dia}"\n---\n'
            f'# Vídeo {vid}\n\n## Resumo\nResumo.\n\n## Boas práticas\n{praticas}\n\n## Ressalvas\n- Opinião do criador.\n\n## Transcrição\n[00:00] x\n',
            encoding="utf-8")
    nota("a", "2026-09-10", "alta", ["miniatura", "retencao"], "- **Rosto grande na miniatura.** Mais clique. [miniatura] [01:00]\n- **Corte a intro.** Retém. [retencao] [02:00]")
    nota("b", "2026-09-12", "media", ["miniatura"], "- **Pouco texto.** Legível no celular. [miniatura] [00:30]")
    nota("c", "2026-09-15", "fora", [], "Não se aplica.")
    return tmp_path


def test_praticas_por_tema_so_do_que_serve(base):
    r = cc.consultar(["miniatura", "retencao"], limite=5)
    mini = r["temas"]["miniatura"]
    assert [n["titulo"] for n in mini] == ["Vídeo a", "Vídeo b"]  # alta antes de média
    assert mini[0]["praticas"] == ["**Rosto grande na miniatura.** Mais clique. [miniatura] [01:00]"]
    assert r["temas"]["retencao"][0]["praticas"] == ["**Corte a intro.** Retém. [retencao] [02:00]"]
    assert mini[0]["ressalvas"] == ["Opinião do criador."]
    assert r["notas_consultadas"] == 2


def test_main_grava_saida(base, capsys):
    saida = base / "rel" / "cerebro.json"
    assert cc.main(["--temas", "miniatura", "--saida", str(saida)]) == 0
    assert json.loads(saida.read_text())["temas"]["miniatura"]


def test_perfis_usam_so_temas_da_taxonomia_real():
    ids = {t["id"] for t in json.loads((RAIZ_REAL / "cerebro" / "temas.json").read_text(encoding="utf-8"))["temas"]}
    for perfil, temas in cc.PROPOSITOS.items():
        assert set(temas) <= ids, (perfil, set(temas) - ids)
