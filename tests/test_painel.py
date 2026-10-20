"""Painel: servidor local com Host, token e limite de corpo; rotas de dados, daily e chat."""
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

import apresentacao
import chat
import daily
import decisoes
import painel


@pytest.fixture
def url(tmp_path, monkeypatch):
    for mod in (daily, painel, chat, decisoes, apresentacao):
        monkeypatch.setattr(mod, "RAIZ", tmp_path)
    (tmp_path / "painel").mkdir()
    (tmp_path / "painel" / "index.html").write_text("<html>TOKEN=__TOKEN__</html>")
    (tmp_path / "painel" / "app.js").write_text("console.log(1)")
    (tmp_path / ".env").write_text("SEGREDO=nao-vaza")
    monkeypatch.setattr(painel, "PAGINA", tmp_path / "painel" / "index.html")
    monkeypatch.setattr(painel, "ESTATICOS", tmp_path / "painel")
    srv = painel.servidor(0)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def chama(url, corpo=None, cabecalhos=None):
    dados = json.dumps(corpo).encode() if isinstance(corpo, (dict, list)) else corpo
    req = urllib.request.Request(url, data=dados, headers=cabecalhos or {}, method="POST" if dados is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def com_token(extra=None):
    return {"X-Painel-Token": painel.TOKEN, "Content-Type": "application/json", **(extra or {})}


def test_pagina_traz_o_token_e_kpis_vazio_sem_analise(url):
    status, corpo = chama(url + "/")
    assert status == 200 and painel.TOKEN in corpo.decode()
    status, corpo = chama(url + "/api/kpis")
    assert status == 200 and json.loads(corpo) == {}


def test_post_sem_token_ou_host_de_fora_da_403(url):
    assert chama(url + "/api/novo", {"tipo": "tarefa", "texto": "x"})[0] == 403
    assert chama(url + "/api/novo", {"tipo": "tarefa", "texto": "x"}, com_token({"Host": "evil.com"}))[0] == 403
    assert chama(url + "/api/kpis", None, {"Host": "evil.com"})[0] == 403


def test_corpo_grande_demais_e_json_invalido(url):
    assert chama(url + "/api/novo", b"x" * (65 * 1024), com_token())[0] == 413
    assert chama(url + "/api/novo", b"{quebrado", com_token())[0] == 400


def test_estaticos_so_de_dentro_do_painel(url):
    assert chama(url + "/estatico/app.js")[0] == 200
    assert chama(url + "/estatico/../.env")[0] == 404
    assert chama(url + "/estatico/%2e%2e/.env")[0] == 404
    assert b"nao-vaza" not in chama(url + "/estatico/..%2f.env")[1]


def test_rotas_de_dados(url, tmp_path, monkeypatch):
    # Decisões também entram em /api/dias; fixar o relógio junto à data dos relatórios.
    monkeypatch.setattr(decisoes.comum, 'agora_iso', lambda: '2026-09-23T12:00:00-03:00')
    pasta = tmp_path / "editorial" / "analises" / "relatorios" / "2026-09-23"
    pasta.mkdir(parents=True)
    (pasta / "diagnostico.json").write_text(json.dumps({"kpis": {"janela": {"desde": "2026-09-14", "ate": "2026-09-21"},
                                                                 "basicas": [], "performance": [], "series": {}}}))
    decisoes.registrar("pauta", "Priorizar Shorts", "dados", "diag", "voltar")
    assert json.loads(chama(url + "/api/kpis")[1])["data"] == "2026-09-23"
    assert json.loads(chama(url + "/api/dias")[1])[0]["data"] == "2026-09-23"
    assert json.loads(chama(url + "/api/dia?data=2026-09-23")[1])["data"] == "2026-09-23"
    assert chama(url + "/api/dia?data=../../x")[0] == 400
    assert json.loads(chama(url + "/api/decisoes")[1])[0]["o_que"] == "Priorizar Shorts"
    assert json.loads(chama(url + "/api/daily")[1]) == {"itens": [], "pensando": []}
    assert chama(url + "/api/nada")[0] == 404


def test_porta_padrao_8766():
    import inspect
    assert inspect.signature(painel.servidor).parameters["porta"].default == 8766


def test_fluxo_da_daily_pelo_painel(url):
    status, corpo = chama(url + "/api/novo", {"tipo": "tarefa", "texto": "Compare os formatos", "para": "analista", "titulo": "Formatos"}, com_token())
    assert status == 200 and json.loads(corpo)["id"] == "d001"
    [fio] = json.loads(chama(url + "/api/daily")[1])["itens"]
    assert fio["titulo"] == "Formatos" and fio["para"] == "analista"
    assert chama(url + "/api/responder", {"id": "d001", "texto": "Obrigado"}, com_token())[0] == 200
    s, c = chama(url + "/api/tarefa/mover", {"id": "d001", "coluna": "executando", "revisao": 1}, com_token())
    assert s == 200 and json.loads(c)["item"]["situacao"] == "executando"
    assert chama(url + "/api/tarefa/editar", {"id": "d001", "titulo": "T", "texto": "X", "revisao": 0}, com_token())[0] == 400
    assert chama(url + "/api/finalizar", {"id": "d001"}, com_token())[0] == 200
    assert chama(url + "/api/encerrar", {"id": "d001"}, com_token())[0] == 400
    assert chama(url + "/api/novo", {"tipo": "tarefa", "texto": "x", "para": "copywriter"}, com_token())[0] == 400


def test_chat_ocupado_da_409_e_canais(url, monkeypatch):
    liberar = threading.Event()
    monkeypatch.setattr(painel, "responder_no_chat", lambda *a: liberar.wait(5) or painel.digitando.pop(a[0], None))
    corpo = {"canal": "analista", "texto": "Como foram as views?"}
    s, c = chama(url + "/api/chat", corpo, com_token())
    assert s == 200 and json.loads(c)["sessao"] == chat.sessao_do_canal("analista")
    assert chama(url + "/api/chat", corpo, com_token())[0] == 409
    liberar.set()
    assert chama(url + "/api/chat", {"canal": "inexistente", "texto": "x"}, com_token())[0] == 400
    canais = json.loads(chama(url + "/api/chat/canais")[1])
    assert [c["id"] for c in canais["equipe"]] == list(chat.EQUIPE)
    estado = json.loads(chama(url + f"/api/chat?sessao={chat.sessao_do_canal('analista')}")[1])
    assert estado["sessao"] == chat.sessao_do_canal("analista")
    assert chama(url + "/api/chat?sessao=../x")[0] == 400


def test_ao_vivo_so_leitura(url, monkeypatch):
    chamadas = []

    class R:
        returncode, stdout, stderr = 0, "As views caíram por causa do feriado.", ""

    def run(cmd, **kw):
        chamadas.append(cmd)
        return R()
    monkeypatch.setattr(painel.subprocess, "run", run)
    chama(url + "/api/novo", {"tipo": "pergunta", "texto": "Por que caiu?", "para": "analista"}, com_token())
    assert json.loads(chama(url + "/api/ao-vivo", {"id": "d001"}, com_token())[1])["pensando"]
    for _ in range(50):
        if daily.item("d001")["status"] == "respondida":
            break
        threading.Event().wait(0.05)
    cmd = chamadas[0]
    assert cmd[cmd.index("--tools") + 1] == "Read,Grep,Glob"
    assert "tokens/" in cmd[cmd.index("--disallowedTools") + 1]
    fio = daily.item("d001")
    assert fio["status"] == "respondida" and fio["mensagens"][-1]["autor"] == "analista"


def test_relatorios_pelo_painel(url, tmp_path):
    pasta = tmp_path / "editorial" / "analises" / "relatorios" / "2026-09-23"
    pasta.mkdir(parents=True)
    (pasta / "diagnostico.json").write_text(json.dumps({"kpis": {"janela": {"desde": "2026-09-14", "ate": "2026-09-21"},
                                                                 "basicas": [], "performance": [], "series": {}}}))
    status, corpo = chama(url + "/api/relatorios")
    assert status == 200 and len(json.loads(corpo)["relatorios"]) >= 25
    assert chama(url + "/api/relatorios?data=../../.env")[0] == 400


def _nota(pasta, vid, status, relevancia, temas, secao, itens):
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / f"2026-09-10-{vid}.md").write_text(
        f'---\nid: "{vid}"\ntitulo: "Vídeo {vid}"\ncanal: "{pasta.name}"\nurl: "https://www.youtube.com/watch?v={vid}"\n'
        f'publicado_em: "2026-09-10"\nstatus: "{status}"\nrelevancia: {json.dumps(relevancia)}\ntemas: {json.dumps(temas)}\n---\n'
        f'# Vídeo {vid}\n\n## Resumo\nResumo {vid}.\n\n## {secao}\n{itens}\n\n## Ressalvas\n- cuidado\n', encoding="utf-8")


def test_conhecimento_resumo_e_busca(url, tmp_path):
    (tmp_path / "cerebro").mkdir()
    (tmp_path / "cerebro" / "canais.json").write_text(json.dumps({"canais": [{"id": "paddy", "nome": "Paddy", "ativo": True}]}))
    (tmp_path / "cerebro" / "temas.json").write_text(json.dumps({"temas": [{"id": "miniatura", "nome": "Miniatura"}]}))
    _nota(tmp_path / "cerebro" / "videos" / "paddy", "a", "destilado", "alta", ["miniatura"], "Boas práticas", "- **Rosto.** [miniatura] [00:10]")
    _nota(tmp_path / "cerebro" / "videos" / "paddy", "b", "bruto", None, [], "Boas práticas", "_pendente_")
    _nota(tmp_path / "cerebro" / "videos" / "paddy", "c", "destilado", "fora", [], "Boas práticas", "Não se aplica.")
    r = json.loads(chama(url + "/api/conhecimento")[1])
    c = r["cerebro"]
    assert c["notas"] == 3 and c["destiladas"] == 2 and c["uteis"] == 1
    assert c["canais"][0] == {"id": "paddy", "nome": "Paddy", "ativo": True, "notas": 3, "destiladas": 2}
    assert c["temas"] == [{"id": "miniatura", "nome": "Miniatura", "notas": 1}]
    assert r["biblioteca"]["notas"] == 0
    achadas = json.loads(chama(url + "/api/conhecimento/buscar?base=cerebro&tema=miniatura")[1])
    assert [n["id"] for n in achadas] == ["a"] and "Rosto" in achadas[0]["itens"]
    assert chama(url + "/api/conhecimento/buscar?base=../../etc&tema=x")[0] == 400


def test_escritorio_so_fala_o_que_esta_nos_arquivos(url, tmp_path):
    r = json.loads(chama(url + "/api/escritorio")[1])
    assert [a["id"] for a in r["equipe"]] == list(chat.EQUIPE)
    assert {f["quem"] for f in r["falas"]} == {"planejador"}  # sem análise nem bases, só o planejador abre e fecha
    assert r["kpis"] == {} and r["serie_views"] == []
    pasta = tmp_path / "editorial" / "analises" / "relatorios" / "2026-09-23"
    pasta.mkdir(parents=True)
    kpi = lambda i, n, v, a: {"id": i, "nome": n, "valor": v, "anterior": a, "variacao_pct": None, "unidade": ""}
    (pasta / "diagnostico.json").write_text(json.dumps({"canal": {"titulo": "Canal", "handle": "@canal"}, "kpis": {
        "janela": {"desde": "2026-09-15", "ate": "2026-09-22"}, "basicas": [kpi("views", "Views", 1767, 1806), kpi("inscritos_ganhos", "Inscritos ganhos", 31, 34),
                                                                            kpi("inscritos", "Inscritos", 9630, None)],
        "performance": [kpi("taxa_engajamento", "Engajamento", 4.75, 3.82)], "series": {"views": [{"dia": "2026-09-21", "valor": 260}]}}}))
    (pasta / "leitura.json").write_text(json.dumps({"tese": "Semana estável com mais engajamento."}))
    _nota(tmp_path / "cerebro" / "videos" / "vidiq", "a", "destilado", "alta", ["miniatura"], "Boas práticas", "- x")
    painel._cache_bases.clear()
    r = json.loads(chama(url + "/api/escritorio")[1])
    falas = " ".join(f["texto"] for f in r["falas"] if f["quem"] == "analista")
    assert "Semana estável" in falas and "1.767" in falas and "31" in falas
    assert any(f["quem"] == "curador" for f in r["falas"])
    assert r["kpis"] == {"views": 1767, "inscritos_ganhos": 31, "inscritos": 9630, "taxa_engajamento": 4.75}
    assert r["serie_views"] == [{"dia": "2026-09-21", "valor": 260}] and r["handle"] == "@canal"
    presentes = {a["id"] for a in r["equipe"] if a["presente"]}
    assert "reviewer" not in presentes and {"planejador", "analista", "curador"} <= presentes


def test_grafo_liga_base_canal_video_e_tema(url, tmp_path):
    (tmp_path / "cerebro").mkdir(exist_ok=True)
    (tmp_path / "cerebro" / "temas.json").write_text(json.dumps({"temas": [{"id": "miniatura", "nome": "Miniatura", "cobre": "thumbnail"}]}))
    _nota(tmp_path / "cerebro" / "videos" / "vidiq", "a", "destilado", "alta", ["miniatura"], "Boas práticas", "- x")
    _nota(tmp_path / "cerebro" / "videos" / "vidiq", "b", "bruto", None, [], "Boas práticas", "_pendente_")
    painel._cache_grafo.clear()
    g = json.loads(chama(url + "/api/grafo")[1])
    ids = {n["id"]: n for n in g["nos"]}
    assert ids["canal"]["tipo"] == "nucleo" and ids["cerebro"]["videos"] == 2 and ids["cerebro"]["destilados"] == 1
    assert ids["biblioteca"]["videos"] == 0
    assert ids["cerebro:tema:miniatura"]["nome"] == "Miniatura"
    elos = {tuple(e) for e in g["elos"]}
    assert ("canal", "cerebro") in elos and ("cerebro", "cerebro:canal:vidiq") in elos
    assert ("cerebro:canal:vidiq", "cerebro:video:a") in elos and ("cerebro:video:a", "cerebro:tema:miniatura") in elos
    assert not any(e[0] == "cerebro:video:b" for e in elos)  # bruto só se liga ao canal


# ---------- apresentações ----------

def _deck_no_disco(tmp_path, slug, score, titulo="Deck", render=False):
    from tests.decks import deck as deck_ok
    d = deck_ok(slug=slug, titulo=titulo)
    pasta = tmp_path / "apresentacoes" / "decks" / slug
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "deck.json").write_text(json.dumps(d, ensure_ascii=False))
    apresentacao.validar(slug, score, "afinidade 22/25 com o top views (6724 views), gancho 20/25, tracao 21/25, atualidade 22/25")
    if render:
        (pasta / "saida").mkdir(exist_ok=True)
        (pasta / "saida" / "capa.png").write_bytes(b"\x89PNG capa")
        (pasta / "saida" / "slide-01.mp4").write_bytes(b"mp4")
        (pasta / "saida" / "palco.html").write_text("<html><video></video></html>")
        (pasta / "saida" / "deck-render.json").write_text("{}")
    return slug


def test_apresentacoes_lista_por_score_e_muda_status(url, tmp_path):
    _deck_no_disco(tmp_path, "2026-09-23-a", 81)
    _deck_no_disco(tmp_path, "2026-09-23-b", 95, render=True)
    _deck_no_disco(tmp_path, "2026-09-23-c", 40)
    status, corpo = chama(url + "/api/apresentacoes")
    r = json.loads(corpo)
    assert status == 200 and [d["slug"] for d in r["abertas"]] == ["2026-09-23-b", "2026-09-23-a"]
    assert r["abertas"][0]["capa"] is True and r["abertas"][1]["capa"] is False
    assert [d["slug"] for d in r["descartadas"]] == ["2026-09-23-c"] and r["gravadas"] == [] and r["fila"] == []
    status, corpo = chama(url + "/api/apresentacao/status", {"slug": "2026-09-23-b", "status": "gravada"}, com_token())
    assert status == 200 and json.loads(corpo)["status"] == "gravada"
    r = json.loads(chama(url + "/api/apresentacoes")[1])
    assert [d["slug"] for d in r["abertas"]] == ["2026-09-23-a"] and [d["slug"] for d in r["gravadas"]] == ["2026-09-23-b"]
    status, corpo = chama(url + "/api/apresentacao/status", {"slug": "2026-09-23-c", "status": "aberta"}, com_token())
    assert status == 400 and "descartada" in json.loads(corpo)["erro"]
    assert chama(url + "/api/apresentacao/status", {"slug": "2026-09-23-a", "status": "apagada"}, com_token())[0] == 400
    assert chama(url + "/api/apresentacao/status", {"slug": "../x", "status": "gravada"}, com_token())[0] == 400
    assert chama(url + "/api/apresentacao/status", {"slug": "2026-09-23-a", "status": "gravada"})[0] == 403


def test_apresentacoes_com_estado_corrompido_da_400_sem_derrubar(url, tmp_path):
    _deck_no_disco(tmp_path, "2026-09-23-a", 81)
    (tmp_path / "apresentacoes" / "decks" / "2026-09-23-a" / "estado.json").write_text("{corrompido")
    status, corpo = chama(url + "/api/apresentacoes")
    assert status == 400 and "estado.json" in json.loads(corpo)["erro"]
    assert chama(url + "/api/kpis")[0] == 200  # o servidor continua de pé


def test_arquivos_da_apresentacao_so_da_saida_e_sem_traversal(url, tmp_path):
    _deck_no_disco(tmp_path, "2026-09-23-b", 95, render=True)
    status, corpo = chama(url + "/apresentacao/2026-09-23-b/capa.png")
    assert status == 200 and corpo == b"\x89PNG capa"
    req = urllib.request.Request(url + "/apresentacao/2026-09-23-b/palco.html")
    with urllib.request.urlopen(req, timeout=5) as r:
        assert r.status == 200 and r.headers["Content-Type"].startswith("text/html") and r.headers["Cache-Control"] == "no-store"
    with urllib.request.urlopen(url + "/apresentacao/2026-09-23-b/slide-01.mp4", timeout=5) as r:
        assert r.status == 200 and r.headers["Content-Type"] == "video/mp4"
    for ruim in ("/apresentacao/2026-09-23-b/deck-render.json", "/apresentacao/2026-09-23-b/../deck.json", "/apresentacao/2026-09-23-b/%2e%2e/deck.json",
                 "/apresentacao/2026-09-23-b/..%2f..%2f..%2f.env", "/apresentacao/nao-existe/capa.png", "/apresentacao/2026-09-23-b/", "/apresentacao/2026-09-23-b/nada.png"):
        status, corpo = chama(url + ruim)
        assert status == 404 and b"nao-vaza" not in corpo, ruim


def test_escritorio_fala_das_apresentacoes_so_com_deck(url, tmp_path):
    r = json.loads(chama(url + "/api/escritorio")[1])
    assert not {f["quem"] for f in r["falas"]} & {"apresentador", "validador"}
    _deck_no_disco(tmp_path, "2026-09-23-b", 95, titulo="Supabase no lugar do backend", render=True)
    apresentacao.pauta("Pauta na fila", "angulo", "top:v00", 84, "afinidade 22/25 com o top views (6724 views), gancho 20/25, tracao 21/25, atualidade 21/25")
    r = json.loads(chama(url + "/api/escritorio")[1])
    falas = {f["quem"]: f["texto"] for f in r["falas"]}
    assert "Supabase no lugar do backend" in falas["apresentador"] and "95" in falas["validador"] and "1" in falas["validador"]
    # "presente" sai de chat.EQUIPE; os dois entram na equipe na sprint 05 e o test_chat prende isso


def test_escritorio_js_tem_visual_e_lugar_dos_agentes_novos():
    js = (Path(painel.__file__).resolve().parent / "painel" / "escritorio.js").read_text(encoding="utf-8")
    visual = js[js.index("const VISUAL"):js.index("const LUGAR")]
    lugar = js[js.index("const LUGAR"):js.index("};", js.index("const LUGAR"))]
    for agente in ("apresentador", "validador"):
        assert f"{agente}:" in visual and f"{agente}:" in lugar, agente
