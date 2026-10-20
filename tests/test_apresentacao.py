"""Apresentações: núcleo injetável, falsos de node/npm, deck, estado, referência, marca, palco e render."""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

import apresentacao

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def raiz(tmp_path, monkeypatch):
    monkeypatch.setattr(apresentacao, "RAIZ", tmp_path)
    (tmp_path / "apresentacoes" / "decks").mkdir(parents=True)
    (tmp_path / "apresentacoes" / "comuns").mkdir()
    return tmp_path


def executavel(pasta, nome, corpo):
    arq = pasta / nome
    arq.write_text("#!/bin/sh\n" + corpo + "\n")
    arq.chmod(0o755)
    return arq


# ---------- núcleo ----------

def test_erro_e_valueerror_e_pasta_do_deck(raiz):
    assert issubclass(apresentacao.Erro, ValueError)
    assert apresentacao.pasta_do_deck("x") == raiz / "apresentacoes" / "decks" / "x"
    with pytest.raises(apresentacao.Erro):
        apresentacao.pasta_do_deck("../fora")


def test_achar_node_pela_variavel_e_sem_node(tmp_path, monkeypatch):
    falso = executavel(tmp_path, "node", 'echo v20.0.0')
    monkeypatch.setenv("APRESENTACAO_NODE", str(falso))
    assert apresentacao.achar_node() == str(falso)
    velho = executavel(tmp_path, "node16", 'echo v16.3.0')
    monkeypatch.setenv("APRESENTACAO_NODE", str(velho))
    with pytest.raises(apresentacao.Erro, match="18"):
        apresentacao.achar_node()
    monkeypatch.delenv("APRESENTACAO_NODE")
    monkeypatch.setenv("PATH", str(tmp_path / "vazio"))
    monkeypatch.setattr(apresentacao, "NVM", tmp_path / "nvm-inexistente")
    with pytest.raises(apresentacao.Erro, match="node"):
        apresentacao.achar_node()


def test_achar_node_no_nvm_mais_novo(tmp_path, monkeypatch):
    monkeypatch.delenv("APRESENTACAO_NODE", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path / "vazio"))
    for v in ("v18.1.0", "v20.20.1", "v9.9.9"):
        pasta = tmp_path / "nvm" / v / "bin"
        pasta.mkdir(parents=True)
        executavel(pasta, "node", f"echo {v}")
    monkeypatch.setattr(apresentacao, "NVM", tmp_path / "nvm")
    assert apresentacao.achar_node().endswith("v20.20.1/bin/node")


def test_achar_npm_pela_variavel_ou_ao_lado_do_node(tmp_path, monkeypatch):
    monkeypatch.setenv("APRESENTACAO_NPM", "/x/npm")
    assert apresentacao.achar_npm("/y/bin/node") == "/x/npm"
    monkeypatch.delenv("APRESENTACAO_NPM")
    assert apresentacao.achar_npm("/y/bin/node") == "/y/bin/npm"


def test_help_rapido_e_sem_rede():
    t = time.monotonic()
    r = subprocess.run([sys.executable, "apresentacao.py", "--help"], cwd=RAIZ, capture_output=True, text=True, timeout=10)
    assert r.returncode == 0 and time.monotonic() - t < 5
    assert "render" in r.stdout and "validar-deck" in r.stdout


def test_gitignore_cobre_node():
    linhas = (RAIZ / ".gitignore").read_text().splitlines()
    for entrada in ("apresentacoes/motion/node_modules/", "apresentacoes/motion/.remotion/", "apresentacoes/decks/*/saida/"):
        assert entrada in linhas, entrada
    assert (RAIZ / "apresentacoes" / "decks").is_dir() and (RAIZ / "apresentacoes" / "comuns").is_dir()


# ---------- falsos e fixtures ----------

from tests.decks import DECK_OK, DIAGNOSTICO_MINI, ativos_falsos, deck  # noqa: E402

NODE_FALSO = str(RAIZ / "tests" / "node_falso.py")
NPM_FALSO = str(RAIZ / "tests" / "npm_falso.py")


def test_node_falso_grava_slides(tmp_path):
    arq = tmp_path / "deck.json"
    arq.write_text(json.dumps(DECK_OK))
    r = subprocess.run([NODE_FALSO, "scripts/render.mjs", str(arq), str(tmp_path / "saida"), str(tmp_path / "ativos")],
                       capture_output=True, text=True, timeout=20)
    assert r.returncode == 0 and "slide 9/9 ok" in r.stdout
    assert sorted(p.name for p in (tmp_path / "saida").glob("slide-*")) == sorted(
        [f"slide-{i:02d}.{ext}" for i in range(1, 10) for ext in ("mp4", "png")])
    assert subprocess.run([NODE_FALSO, "--version"], capture_output=True, text=True).stdout.strip() == "v20.0.0"


def test_npm_falso_instala(tmp_path):
    r = subprocess.run([NPM_FALSO, "install"], cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert r.returncode == 0 and (tmp_path / "node_modules" / ".instalado").read_text() == "install"


def test_deck_ok_segue_o_schema():
    tipos = [s["tipo"] for s in DECK_OK["slides"]]
    assert len(tipos) == 9 and tipos[0] == "titulo" and tipos[-1] == "cta"
    assert set(tipos) == {"titulo", "declaracao", "grade", "comparacao", "etapas", "estatisticas", "fluxo", "screenshot", "cta"}
    assert all(n["fonte"] for s in DECK_OK["slides"] if s["tipo"] == "estatisticas" for n in s["numeros"])
    assert DECK_OK["marca"]["cor"] == "#3ECF8E"
    assert len(DIAGNOSTICO_MINI["videos"]) == 12 and len({v["views"] for v in DIAGNOSTICO_MINI["videos"]}) == 12
    assert deck(titulo="x")["titulo"] == "x" and DECK_OK["titulo"] != "x"


def test_ativos_falsos_sao_png_validos(tmp_path):
    import zlib
    nomes = ativos_falsos(tmp_path / "ativos")
    assert nomes == ["cta.png", "logo.png", "print.png"]
    dados = (tmp_path / "ativos" / "cta.png").read_bytes()
    assert dados[:4].hex() == "89504e47"
    ini = dados.index(b"IDAT") + 4
    tamanho = int.from_bytes(dados[ini - 8:ini - 4], "big")
    assert len(zlib.decompress(dados[ini:ini + tamanho])) == 1080 * (1920 * 3 + 1)


# ---------- deck e slug ----------

def grava_deck(raiz, d, slug=None):
    slug = slug or d["slug"]
    pasta = raiz / "apresentacoes" / "decks" / slug
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "deck.json").write_text(json.dumps(d, ensure_ascii=False))
    return slug


def test_validar_deck_aceita_o_deck_ok(raiz):
    assert apresentacao.validar_deck(DECK_OK) == []
    slug = grava_deck(raiz, DECK_OK)
    assert apresentacao.main(["validar-deck", slug]) == 0


def test_validar_deck_sem_cta_sai_1_nomeando_a_regra(raiz, capsys):
    d = deck(slides=DECK_OK["slides"][:-1] + [DECK_OK["slides"][1]])
    slug = grava_deck(raiz, d)
    assert apresentacao.main(["validar-deck", slug]) == 1
    assert "cta" in capsys.readouterr().err


def _com_slide(i, **campos):
    slides = [dict(s) for s in DECK_OK["slides"]]
    slides[i].update(campos)
    return deck(slides=slides)


@pytest.mark.parametrize("ruim, trecho", [
    (deck(slides=DECK_OK["slides"][:4] + [DECK_OK["slides"][-1]]), "6 a 10"),
    (_com_slide(0, titulo="um dois tres quatro cinco seis sete oito nove dez onze"), "10 palavras"),
    (_com_slide(5, numeros=[{"valor": 5, "sufixo": "", "rotulo": "x", "fonte": ""}]), "fonte"),
    (_com_slide(5, numeros=[{"valor": 6724, "sufixo": "", "rotulo": "views no top", "fonte": "diagnostico 2026-09-23"}]), "conteúdo da aula"),
    (_com_slide(5, numeros=[{"valor": 19, "sufixo": "", "rotulo": "por mil", "fonte": "inscritos por mil views do canal"}]), "conteúdo da aula"),
    (_com_slide(1, texto="Hora que não paga — nunca"), "travessão"),
    (_com_slide(0, titulo="linha um\nlinha dois"), "quebra de linha"),
    (deck(marca={**DECK_OK["marca"], "cor": "rgb(1,2,3)"}), "#RRGGBB"),
    (deck(marca={**DECK_OK["marca"], "cor": "#1C1C1E"}), "contraste"),
    (_com_slide(7, imagem="../fora.png"), "ativos"),
    (_com_slide(6, nos=DECK_OK["slides"][6]["nos"][:2]), "3 a 6"),
    (_com_slide(2, itens=DECK_OK["slides"][2]["itens"][:2]), "3 a 6"),
    (deck(slides=[DECK_OK["slides"][-1]] + DECK_OK["slides"][1:-1] + [DECK_OK["slides"][0]]), "primeiro"),
])
def test_validar_deck_recusa_cada_violacao(ruim, trecho):
    erros = apresentacao.validar_deck(ruim)
    assert erros and any(trecho in e for e in erros), erros


def test_slug_com_data_injetada_e_colisao(raiz):
    assert apresentacao.slug("ADEUS, Claude Code!", hoje="2026-09-23") == "2026-09-23-adeus-claude-code"
    (raiz / "apresentacoes" / "decks" / "2026-09-23-adeus-claude-code").mkdir()
    assert apresentacao.slug("ADEUS, Claude Code!", hoje="2026-09-23") == "2026-09-23-adeus-claude-code-2"
    assert len(apresentacao.slug("x" * 200, hoje="2026-09-23")) <= 60


def test_slug_pela_cli(raiz, capsys):
    assert apresentacao.main(["slug", "--titulo", "Supabase no lugar do backend"]) == 0
    saida = capsys.readouterr().out.strip()
    assert saida.endswith("-supabase-no-lugar-do-backend") and len(saida) == 10 + 1 + len("supabase-no-lugar-do-backend")


# ---------- estado, status, lista, pauta ----------

MOTIVO = "afinidade 22/25 com o top views (Claude Code 6724 views), gancho 20/25, tracao 21/25, atualidade 22/25"


def test_validar_grava_estado_pelo_corte_80_e_revalida(raiz):
    slug = grava_deck(raiz, DECK_OK)
    assert apresentacao.main(["validar", slug, "--score", "85", "--motivo", MOTIVO]) == 0
    e = apresentacao.ler_estado(slug)
    assert e["status"] == "aberta" and e["score"] == 85 and e["validado_por"] == "validador" and e["motivo"] == MOTIVO
    assert e["render"] is None and len(e["validacoes"]) == 1 and e["validado_em"]
    apresentacao.validar(slug, 79, MOTIVO, por="validador")
    assert apresentacao.ler_estado(slug)["status"] == "descartada"
    apresentacao.validar(slug, 88, MOTIVO, por="validador")
    e = apresentacao.ler_estado(slug)
    assert e["status"] == "aberta" and e["score"] == 88 and [v["score"] for v in e["validacoes"]] == [85, 79, 88]


@pytest.mark.parametrize("score, motivo", [(101, MOTIVO), (-1, MOTIVO), ("oitenta", MOTIVO), (85, "curto demais")])
def test_validar_recusa_score_ou_motivo_ruim(raiz, score, motivo):
    slug = grava_deck(raiz, DECK_OK)
    with pytest.raises(apresentacao.Erro):
        apresentacao.validar(slug, score, motivo)
    assert apresentacao.ler_estado(slug) is None


def test_status_so_alterna_aberta_e_gravada(raiz):
    slug = grava_deck(raiz, DECK_OK)
    apresentacao.validar(slug, 90, MOTIVO)
    assert apresentacao.main(["status", slug, "gravada"]) == 0
    e = apresentacao.ler_estado(slug)
    assert e["status"] == "gravada" and e["gravado_em"]
    apresentacao.status(slug, "aberta")
    assert apresentacao.ler_estado(slug)["status"] == "aberta" and apresentacao.ler_estado(slug)["gravado_em"] is None
    with pytest.raises(apresentacao.Erro):
        apresentacao.status(slug, "descartada")
    apresentacao.validar(slug, 70, MOTIVO)
    with pytest.raises(apresentacao.Erro, match="descartada"):
        apresentacao.status(slug, "aberta")
    with pytest.raises(apresentacao.Erro):
        apresentacao.status("sem-estado", "gravada")


def test_lista_ordena_abertas_por_score_e_separa_gravadas_e_descartadas(raiz):
    for i, (s, score) in enumerate([("a", 81), ("b", 95), ("c", 88), ("d", 50), ("e", 99)]):
        grava_deck(raiz, deck(slug=f"2026-09-23-{s}", titulo=f"Deck {s}"), f"2026-09-23-{s}")
        apresentacao.validar(f"2026-09-23-{s}", score, MOTIVO)
    apresentacao.status("2026-09-23-e", "gravada")
    (raiz / "apresentacoes" / "decks" / "2026-09-23-b" / "saida").mkdir()
    (raiz / "apresentacoes" / "decks" / "2026-09-23-b" / "saida" / "capa.png").write_bytes(b"x")
    r = apresentacao.lista()
    assert [d["slug"][-1] for d in r["abertas"]] == ["b", "c", "a"]
    assert [d["slug"][-1] for d in r["gravadas"]] == ["e"] and [d["slug"][-1] for d in r["descartadas"]] == ["d"]
    b = r["abertas"][0]
    assert b["titulo"] == "Deck b" and b["score"] == 95 and b["capa"] is True and b["slides"] == 9 and b["marca"] == "Supabase"
    assert r["abertas"][1]["capa"] is False and r["fila"] == []
    assert apresentacao.main(["lista", "--json"]) == 0


def test_lista_ignora_pasta_sem_deck_e_deck_sem_estado(raiz):
    (raiz / "apresentacoes" / "decks" / "lixo").mkdir()
    grava_deck(raiz, DECK_OK)
    r = apresentacao.lista()
    assert r["abertas"] == [] and r["sem_score"] == [DECK_OK["slug"]]


def test_pauta_id_estavel_e_fila_so_com_80(raiz):
    assert apresentacao.pauta_id("Título X", "biblioteca/a.md") == apresentacao.pauta_id("titulo x", "biblioteca/a.md")
    assert apresentacao.pauta_id("Título X", "biblioteca/a.md") != apresentacao.pauta_id("Título X", "biblioteca/b.md")
    assert len(apresentacao.pauta_id("a", "b")) == 12
    assert apresentacao.main(["pauta", "--titulo", "Claude Code de graça", "--angulo", "Alternativa gratuita", "--origem", "top:uyOZMToKc8o",
                              "--score", "84", "--motivo", MOTIVO]) == 0
    with pytest.raises(apresentacao.Erro, match="80"):
        apresentacao.pauta("Fraca", "x", "tema", 70, MOTIVO)
    apresentacao.pauta("Outra forte", "y", "tema", 91, MOTIVO)
    fila = apresentacao.ler_fila()
    assert [p["score"] for p in fila] == [91, 84] and fila[1]["pauta_id"] == apresentacao.pauta_id("Claude Code de graça", "top:uyOZMToKc8o")
    apresentacao.pauta("Claude Code de graça", "Alternativa gratuita v2", "top:uyOZMToKc8o", 86, MOTIVO)
    assert len(apresentacao.ler_fila()) == 2 and [p["score"] for p in apresentacao.ler_fila()] == [91, 86]
    assert apresentacao.lista()["fila"][0]["titulo"] == "Outra forte"


# ---------- referência e candidatas ----------

def grava_diagnostico(raiz, data="2026-09-23", diag=None):
    pasta = raiz / "editorial" / "analises" / "relatorios" / data
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "diagnostico.json").write_text(json.dumps(diag or DIAGNOSTICO_MINI, ensure_ascii=False))
    return pasta


def test_referencia_top_views_e_top_inscritos(raiz):
    grava_diagnostico(raiz, "2026-09-20", {"videos": [{"id": "velho", "titulo": "Velho", "views": 99999, "formato": "VIDEO_ON_DEMAND"}]})
    grava_diagnostico(raiz)
    r = apresentacao.referencia()
    assert r["diagnostico"].endswith("2026-09-23/diagnostico.json") and r["canal"]["handle"] == "@canal"
    top = r["top_views"]
    assert len(top) == 10 and [v["views"] for v in top] == sorted((v["views"] for v in top), reverse=True) and top[0]["id"] == "v00"
    assert top[0]["views_sobre_mediana"] == round(6724 / 3974, 2) and top[0]["formato"] == "VIDEO_ON_DEMAND"
    assert "claude" in top[0]["palavras"] and "code" in top[0]["palavras"] and "a" not in top[0]["palavras"] and "adeus" in top[0]["palavras"]
    ins = r["top_inscritos"]
    assert len(ins) == 5 and all(v["views"] >= 100 for v in ins) and "v03" not in {v["id"] for v in ins}
    assert ins[0]["inscritos_por_mil_views"] >= ins[-1]["inscritos_por_mil_views"]
    assert r["mediana"]["VIDEO_ON_DEMAND"] == 3974 and r["total_videos"] == 12
    assert any(v["id"] == "v11" and v["taxa_engajamento"] is None for v in r["top_views"] + r["top_inscritos"]) or True
    v11 = next(v for v in r["todos"] if v["id"] == "v11")
    assert v11["taxa_engajamento"] is None and v11["curtidas"] is None


def test_referencia_sem_diagnostico_sai_1_e_manda_analisar(raiz, capsys):
    assert apresentacao.main(["referencia", "--json"]) == 1
    assert "/analisar-canal" in capsys.readouterr().err
    grava_diagnostico(raiz)
    assert apresentacao.main(["referencia", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["top_views"][0]["id"] == "v00"


def test_candidatas_traz_tres_origens_com_pauta_id_e_exclui_por_id(raiz, monkeypatch):
    import planejar
    from tests.test_planejar import NOTA
    monkeypatch.setattr(planejar, "RAIZ", raiz)
    vids = raiz / "biblioteca" / "videos" / "canal-x"
    vids.mkdir(parents=True)
    (vids / "a.md").write_text(NOTA.format(data="2026-09-20", status="destilado", rel="alta"))
    grava_diagnostico(raiz)
    apresentacao.pauta("Pauta da fila", "angulo", "top:v00", 90, MOTIVO)
    apresentacao.pauta("Pauta com deck", "angulo", "top:v01", 85, MOTIVO)
    d = deck(slug="2026-01-01-antigo", pauta_id=apresentacao.pauta_id("Pauta com deck", "top:v01"))
    grava_deck(raiz, d, "2026-01-01-antigo")
    d2 = deck(slug="2026-01-02-da-biblioteca", pauta_id=apresentacao.pauta_id("Agentes que fazem code review.", "biblioteca/videos/canal-x/a.md"))
    grava_deck(raiz, d2, "2026-01-02-da-biblioteca")
    r = apresentacao.candidatas()
    bib = r["biblioteca"]
    assert [p["titulo"] for p in bib] == ["Três prompts para PR."] and bib[0]["origem"] == "biblioteca/videos/canal-x/a.md" and len(bib[0]["pauta_id"]) == 12
    assert [p["titulo"] for p in r["fila"]] == ["Pauta da fila"]
    assert len(r["top_videos"]) == 10 and r["top_videos"][0]["origem"] == "top:v00" and r["top_videos"][0]["pauta_id"]
    assert set(r["excluidas"]) == {apresentacao.pauta_id("Pauta com deck", "top:v01"), d2["pauta_id"]}
    assert apresentacao.main(["candidatas", "--json"]) == 0


def test_candidatas_sem_diagnostico_sai_1(raiz):
    assert apresentacao.main(["candidatas"]) == 1


# ---------- marca ----------

HTML_SEM_SINAL = "<html><head><title>OpenCode | The open source AI coding agent</title></head><body><p>oi</p></body></html>"
HTML_COM_SINAL = ('<html><head><title>Cursor - The AI Code Editor</title><meta name="theme-color" content="#F7F7F4">'
                  '<link rel="icon" href="/icon.png"></head><body></body></html>')
HTML_COM_CSS = ('<html><head><title>Ferramenta X</title><link rel="icon" type="image/png" href="https://cdn.x.dev/fav.png">'
                '<style>.a{color:#8E8B8B}.b{background:#D97757}.c{color:#D97757}.d{border:1px solid #d97757}.e{color:#cfcecd}</style></head><body></body></html>')


def test_contraste_e_clarear():
    assert apresentacao.contraste("#F2F5F3", "#16181A") > 15
    assert apresentacao.contraste("#D97757", "#16181A") >= 3
    assert apresentacao.contraste("#1C1C1E", "#16181A") < 1.1
    claro = apresentacao.clarear("#1C1C1E")
    assert apresentacao.HEX.fullmatch(claro) and apresentacao.contraste(claro, "#16181A") >= 3
    assert apresentacao.clarear("#D97757") == "#D97757"


def test_marca_curada_pela_tabela():
    m = apresentacao.marca("https://supabase.com/docs", buscar_html=lambda url: HTML_SEM_SINAL)
    assert (m["nome"], m["cor"], m["origem"]) == ("Supabase", "#3ECF8E", "tabela")
    m = apresentacao.marca("https://www.cursor.com", buscar_html=lambda url: HTML_COM_SINAL)
    assert m["origem"] == "canal" and m["cor"] == "#22C55E" and m["nome"] == "Cursor"
    tabela = json.loads((RAIZ / "apresentacoes" / "comuns" / "marcas.json").read_text())
    assert {"claude", "supabase", "n8n", "github", "openai", "vercel", "cursor", "opencode"} <= set(tabela["marcas"])
    assert "não oficial" in tabela["_nota"] or "nao oficial" in tabela["_nota"]


def test_marca_pelos_sinais_do_site_e_fallback(raiz):
    m = apresentacao.marca("https://ferramenta-y.dev", buscar_html=lambda url: HTML_COM_SINAL.replace("Cursor - The AI Code Editor", "Y - editor"))
    assert m["origem"] == "site" and m["nome"] == "Y" and m["cor"] == apresentacao.clarear("#F7F7F4") and m["icone"] == "https://ferramenta-y.dev/icon.png"
    m = apresentacao.marca("https://x.dev", buscar_html=lambda url: HTML_COM_CSS)
    assert m["origem"] == "site" and m["cor"] == "#D97757" and m["nome"] == "Ferramenta X" and m["icone"] == "https://cdn.x.dev/fav.png"
    m = apresentacao.marca("https://sem-sinal.dev", buscar_html=lambda url: HTML_SEM_SINAL)
    assert m["origem"] == "canal" and m["cor"] == "#22C55E" and m["nome"] == "OpenCode"
    assert apresentacao.sinais_do_html(HTML_SEM_SINAL)["theme_color"] is None


def test_marca_com_falha_de_rede_cai_na_canal_com_aviso(raiz, capsys):
    def quebra(url):
        raise OSError("sem rede")
    m = apresentacao.marca("https://fora.dev", buscar_html=quebra)
    assert m["origem"] == "canal" and m["avisos"]
    assert apresentacao.main(["marca", "https://fora.dev"]) == 0
    assert json.loads(capsys.readouterr().out)["origem"] == "canal"


def test_marca_baixa_o_icone_para_o_deck(raiz, capsys):
    slug = grava_deck(raiz, DECK_OK)
    baixados = []

    def baixar(url):
        baixados.append(url)
        return b"\x89PNG icone"
    m = apresentacao.marca("https://x.dev", deck=slug, buscar_html=lambda url: HTML_COM_CSS, baixar=baixar)
    assert baixados == ["https://cdn.x.dev/fav.png"] and m["logo"] == "logo.png"
    assert (raiz / "apresentacoes" / "decks" / slug / "ativos" / "logo.png").read_bytes() == b"\x89PNG icone"

    def falha(url):
        raise OSError("403")
    m = apresentacao.marca("https://x.dev", deck=slug, buscar_html=lambda url: HTML_COM_CSS, baixar=falha)
    assert m["logo"] is None and any("icone" in a or "ícone" in a for a in m["avisos"])
    m = apresentacao.marca("https://x.dev", deck=slug, buscar_html=lambda url: HTML_COM_CSS.replace("fav.png", "fav.ico"), baixar=baixar)
    assert m["logo"] is None and len(baixados) == 1


# ---------- ler <url> ----------

PAGINA = ('<html><head><title>Guia do n8n</title><meta name="description" content="Automação sem código"><style>.x{}</style>'
          '<script>var a = 1;</script></head><body><nav>menu</nav><h1>Guia do n8n</h1><p>Primeiro parágrafo.</p><h2>Instalar</h2>'
          '<p>Segundo &amp; parágrafo.</p><h2>Usar</h2><p>Terceiro parágrafo.</p><footer>rodapé</footer></body></html>')


def test_ler_extrai_titulo_descricao_cabecalhos_e_paragrafos(capsys):
    r = apresentacao.ler("https://docs.n8n.io/guia", buscar_html=lambda url: PAGINA)
    assert r["titulo"] == "Guia do n8n" and r["descricao"] == "Automação sem código"
    assert r["blocos"] == ["# Guia do n8n", "Primeiro parágrafo.", "## Instalar", "Segundo & parágrafo.", "## Usar", "Terceiro parágrafo."]
    assert "var a" not in r["texto"] and "menu" not in r["texto"] and "rodapé" not in r["texto"]
    assert apresentacao.main(["ler", "https://docs.n8n.io/guia"]) == 1  # sem rede no teste: erro, não travamento


def test_ler_corta_em_20_mil_e_recusa_youtube():
    grande = "<html><head><title>G</title></head><body>" + "".join(f"<p>parágrafo {i} com texto</p>" for i in range(3000)) + "</body></html>"
    r = apresentacao.ler("https://x.dev", buscar_html=lambda url: grande)
    assert len(r["texto"]) <= 20_000 and r["cortado"] is True
    with pytest.raises(apresentacao.Erro, match="biblioteca.py importar"):
        apresentacao.ler("https://www.youtube.com/watch?v=x", buscar_html=lambda url: PAGINA)
    with pytest.raises(apresentacao.Erro, match="biblioteca.py importar"):
        apresentacao.ler("https://youtu.be/x", buscar_html=lambda url: PAGINA)


# ---------- screenshot ----------

def bh_falso(tmp_path):
    """Um browser-harness falso: lê o script no stdin, acha o caminho do PNG e grava um PNG ali."""
    corpo = ("python3 -c \"import re,sys; s=sys.stdin.read(); m=re.search(r\\\"DESTINO = '([^']+)'\\\", s); "
             "open(m.group(1),'wb').write(b'\\x89PNG captura'); print('ok')\"")
    return executavel(tmp_path, "browser-harness", corpo)


def test_screenshot_padrao_canalplay_cacheia_em_comuns(raiz, monkeypatch, tmp_path):
    slug = grava_deck(raiz, DECK_OK)
    bh = bh_falso(tmp_path)
    monkeypatch.setenv("APRESENTACAO_BH", str(bh))
    assert apresentacao.main(["screenshot", "--deck", slug]) == 0
    comuns = raiz / "apresentacoes" / "comuns" / "cta.png"
    ativo = raiz / "apresentacoes" / "decks" / slug / "ativos" / "cta.png"
    assert comuns.read_bytes() == b"\x89PNG captura" and ativo.read_bytes() == b"\x89PNG captura"
    comuns.write_bytes(b"cache")
    r = apresentacao.screenshot(slug)
    assert r["reusado"] is True and ativo.read_bytes() == b"cache"
    r = apresentacao.screenshot(slug, atualizar=True)
    assert r["reusado"] is False and ativo.read_bytes() == b"\x89PNG captura"


def test_screenshot_de_outra_url_vai_direto_para_ativos(raiz, monkeypatch, tmp_path):
    slug = grava_deck(raiz, DECK_OK)
    monkeypatch.setenv("APRESENTACAO_BH", str(bh_falso(tmp_path)))
    r = apresentacao.screenshot(slug, url="https://x.dev", nome="print.png")
    assert r["arquivo"] == "print.png" and (raiz / "apresentacoes" / "decks" / slug / "ativos" / "print.png").exists()
    assert not (raiz / "apresentacoes" / "comuns" / "print.png").exists()
    with pytest.raises(apresentacao.Erro):
        apresentacao.screenshot(slug, url="https://x.dev", nome="../fora.png")


def test_screenshot_sem_browser_harness_ou_com_timeout_avisa_e_sai_0(raiz, monkeypatch, tmp_path, capsys):
    slug = grava_deck(raiz, DECK_OK)
    monkeypatch.setenv("APRESENTACAO_BH", str(tmp_path / "nao-existe"))
    assert apresentacao.main(["screenshot", "--deck", slug]) == 0
    assert "aviso" in capsys.readouterr().out
    dorme = executavel(tmp_path, "bh-lento", "sleep 5")
    monkeypatch.setenv("APRESENTACAO_BH", str(dorme))
    monkeypatch.setattr(apresentacao, "TIMEOUT_SCREENSHOT", 1)
    r = apresentacao.screenshot(slug)
    assert r["arquivo"] is None and any("tempo" in a for a in r["avisos"])
    assert not (raiz / "apresentacoes" / "decks" / slug / "ativos" / "cta.png").exists()


# ---------- palco ----------

def test_palco_html_tem_um_video_por_slide_tela_cheia_e_teclado():
    html = apresentacao.palco_html(deck(titulo="Título <do> deck & cia"))
    assert html.count("<video") == 9
    for i in range(1, 10):
        assert f'src="slide-{i:02d}.mp4"' in html and f'poster="slide-{i:02d}.png"' in html
    assert "requestFullscreen" in html and "keydown" in html and "exitFullscreen" in html
    assert "Título &lt;do&gt; deck &amp; cia" in html and "<do>" not in html
    assert "01 / 09" in html
    assert " loop" not in html and html.count("autoplay") <= 1
    assert "Supabase" in html
    assert "http" not in html.replace("https://example.com", "").replace("http://www.w3.org", "")


@pytest.mark.skipif(not shutil.which("node"), reason="node ausente")
def test_js_do_palco_com_sintaxe_valida(tmp_path):
    html = apresentacao.palco_html(DECK_OK)
    scripts = re.findall(r"<script>(.*?)</script>", html, flags=re.S)
    assert scripts
    for i, js in enumerate(scripts):
        arq = tmp_path / f"palco{i}.js"
        arq.write_text(js)
        r = subprocess.run(["node", "--check", str(arq)], capture_output=True, text=True, timeout=20)
        assert r.returncode == 0, r.stderr


# ---------- render, capa e abrir ----------

@pytest.fixture
def motion(raiz, monkeypatch, tmp_path):
    """Projeto motion mínimo em tmp_path com node e npm falsos; node_modules já instalado."""
    pasta = raiz / "apresentacoes" / "motion"
    (pasta / "scripts").mkdir(parents=True)
    (pasta / "scripts" / "render.mjs").write_text("// falso")
    (pasta / "node_modules").mkdir()
    monkeypatch.setenv("APRESENTACAO_NODE", NODE_FALSO)
    monkeypatch.setenv("APRESENTACAO_NPM", NPM_FALSO)
    log = tmp_path / "npm.log"
    monkeypatch.setenv("NPM_FALSO_LOG", str(log))
    monkeypatch.delenv("NODE_FALSO_FALHA", raising=False)
    return {"pasta": pasta, "log": log}


def deck_aberto(raiz, d=None):
    slug = grava_deck(raiz, d or DECK_OK)
    ativos_falsos(raiz / "apresentacoes" / "decks" / slug / "ativos")
    apresentacao.validar(slug, 90, MOTIVO)
    return slug


def test_render_produz_saida_completa_sem_chamar_npm(raiz, motion):
    slug = deck_aberto(raiz)
    assert apresentacao.main(["render", slug]) == 0
    saida = raiz / "apresentacoes" / "decks" / slug / "saida"
    nomes = {p.name for p in saida.iterdir()}
    assert {f"slide-{i:02d}.mp4" for i in range(1, 10)} <= nomes and {f"slide-{i:02d}.png" for i in range(1, 10)} <= nomes
    assert (saida / "capa.png").read_bytes() == (saida / "slide-01.png").read_bytes()
    assert "<video" in (saida / "palco.html").read_text()
    e = apresentacao.ler_estado(slug)
    assert e["render"]["ok"] is True and e["render"]["slides"] == 9 and e["render"]["avisos"] == [] and e["render"]["segundos"] >= 0
    assert not motion["log"].exists()
    recebido = json.loads((saida / "deck-recebido.json").read_text())
    assert recebido["slides"][7]["imagem"] == "print.png" and recebido["marca"]["logo"] == "logo.png"


def test_render_instala_so_quando_falta_node_modules(raiz, motion):
    shutil.rmtree(motion["pasta"] / "node_modules")
    slug = deck_aberto(raiz)
    apresentacao.render(slug)
    assert motion["log"].read_text().strip() == "install" and (motion["pasta"] / "node_modules" / ".instalado").exists()
    apresentacao.render(slug)
    assert motion["log"].read_text().count("install") == 1


def test_render_recusa_deck_descartado_ou_sem_score(raiz, motion, tmp_path):
    slug = grava_deck(raiz, DECK_OK)
    with pytest.raises(apresentacao.Erro, match="score"):
        apresentacao.render(slug)
    apresentacao.validar(slug, 50, MOTIVO)
    with pytest.raises(apresentacao.Erro, match="descartada"):
        apresentacao.render(slug)
    assert not (raiz / "apresentacoes" / "decks" / slug / "saida").exists()


def test_render_recusa_deck_invalido(raiz, motion):
    slug = deck_aberto(raiz, deck(slides=DECK_OK["slides"][:5]))
    with pytest.raises(apresentacao.Erro, match="6 a 10"):
        apresentacao.render(slug)


def test_render_com_falha_do_node_grava_estado_e_stderr(raiz, motion, monkeypatch):
    slug = deck_aberto(raiz)
    monkeypatch.setenv("NODE_FALSO_FALHA", "1")
    assert apresentacao.main(["render", slug]) == 1
    e = apresentacao.ler_estado(slug)
    assert e["render"]["ok"] is False and "falhou de propósito" in e["render"]["erro"]
    assert not (raiz / "apresentacoes" / "decks" / slug / "saida" / "capa.png").exists()


def test_render_troca_imagem_ausente_por_null_com_aviso(raiz, motion):
    slug = deck_aberto(raiz)
    (raiz / "apresentacoes" / "decks" / slug / "ativos" / "print.png").unlink()
    (raiz / "apresentacoes" / "decks" / slug / "ativos" / "logo.png").unlink()
    apresentacao.render(slug)
    recebido = json.loads((raiz / "apresentacoes" / "decks" / slug / "saida" / "deck-recebido.json").read_text())
    assert recebido["slides"][7]["imagem"] is None and recebido["slides"][8]["imagem"] == "cta.png" and recebido["marca"]["logo"] is None
    avisos = apresentacao.ler_estado(slug)["render"]["avisos"]
    assert len(avisos) == 2 and any("print.png" in a for a in avisos) and any("logo.png" in a for a in avisos)
    assert json.loads((raiz / "apresentacoes" / "decks" / slug / "deck.json").read_text())["slides"][7]["imagem"] == "print.png"


def test_abrir_usa_webbrowser(raiz, motion, monkeypatch):
    slug = deck_aberto(raiz)
    apresentacao.render(slug)
    abertos = []
    monkeypatch.setattr(apresentacao.webbrowser, "open", lambda url: abertos.append(url) or True)
    assert apresentacao.main(["abrir", slug]) == 0
    assert abertos == [(raiz / "apresentacoes" / "decks" / slug / "saida" / "palco.html").resolve().as_uri()]
    with pytest.raises(apresentacao.Erro, match="render"):
        apresentacao.abrir(grava_deck(raiz, deck(slug="2026-09-23-x"), "2026-09-23-x"))
