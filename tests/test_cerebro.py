"""cerebro.py (cérebro de YouTube): só entra vídeo novo, o estado lembra o último, e nota destilada tem que estar completa. Sem rede."""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

import cerebro

CANAL = {"id": "canal-x", "nome": "Canal X", "url": "https://www.youtube.com/@canalx", "channel_id": "UCx", "abas": ["videos"], "ativo": True}


def video(vid, dia, titulo=None):
    return {"id": vid, "titulo": titulo or f"Vídeo {vid}", "publicado_em": dia, "duracao_seg": 600, "idioma": "en", "legenda": "automatica",
            "visualizacoes": 1000, "descricao": "Links:\n## Capítulo falso", "capitulos": [(0, "Intro")], "blocos": [(0, "Fala um."), (65, "Fala dois.")]}


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    """YouTube de mentira: `acervo` é o que o canal tem (mais novo primeiro), `falhas` é o que dá erro ao baixar."""
    m = {"acervo": [video("v3", "2026-09-10"), video("v2", "2026-08-01"), video("v1", "2026-01-15")], "falhas": {}, "baixados": []}

    def listar(url, abas=("videos",), limite=None, idioma=None):
        return {"nome": "Canal X", "channel_id": "UCx",
                "videos": [{"id": v["id"], "titulo": v["titulo"], "duracao_seg": 600, "aba": "videos"} for v in m["acervo"][:limite]]}

    def baixar(vid, idioma=None):
        m["baixados"].append(vid)
        if vid in m["falhas"]:
            raise m["falhas"][vid]
        return next(v for v in m["acervo"] if v["id"] == vid)

    for nome, valor in {"PASTA": tmp_path / "cerebro", "CANAIS": tmp_path / "cerebro" / "canais.json", "TEMAS": tmp_path / "cerebro" / "temas.json",
                        "VIDEOS": tmp_path / "cerebro" / "videos", "INDICE": tmp_path / "cerebro" / "INDEX.md",
                        "ESTADO": tmp_path / "estado" / "cerebro.json", "RAIZ": tmp_path}.items():
        monkeypatch.setattr(cerebro, nome, valor)
    monkeypatch.setattr(cerebro, "listar_canal", listar)
    monkeypatch.setattr(cerebro, "baixar_video", baixar)
    monkeypatch.setattr(cerebro.time, "sleep", lambda _: None)
    cerebro.salvar_canais([dict(CANAL)])
    cerebro.gravar_json(cerebro.TEMAS, {"temas": [{"id": "miniatura", "nome": "Miniatura"}, {"id": "shorts", "nome": "Shorts"}]})
    return m


def rodar(*argv):
    import io
    from contextlib import redirect_stdout
    saida = io.StringIO()
    with redirect_stdout(saida):
        codigo = cerebro.main([*argv, "--json"])
    return codigo, json.loads(saida.getvalue())


def destilar(nota, relevancia="alta", temas='["miniatura"]', corpo=True):
    texto = nota["_arquivo"].read_text(encoding="utf-8")
    texto = texto.replace('status: "bruto"', "status: destilado").replace("relevancia: null", f"relevancia: {relevancia}")
    texto = texto.replace("temas: []", f"temas: {temas}").replace("destilado_em: null", 'destilado_em: "2026-09-19"')
    if corpo:
        texto = texto.replace(cerebro.PENDENTE, "- **Abra com a promessa.** O vídeo mostra retenção maior. `[miniatura]` `[01:05]`")
    nota["_arquivo"].write_text(texto, encoding="utf-8")


def test_importar_traz_o_acervo_e_guarda_o_ultimo_video(mundo):
    _, saida = rodar("importar", "canal-x")
    assert [v["id"] for v in saida["canal-x"]["novos"]] == ["v3", "v2", "v1"]
    estado = json.loads(cerebro.ESTADO.read_text(encoding="utf-8"))["canais"]["canal-x"]
    assert estado["ultimo_video"] == {"id": "v3", "titulo": "Vídeo v3", "publicado_em": "2026-09-10"}
    nota = cerebro.notas("canal-x")[0]
    assert nota["status"] == "bruto" and nota["temas"] == [] and nota["url"].endswith("v=v1")
    assert cerebro.secao(nota["_corpo"], "Transcrição").startswith("[00:00] Fala um.")
    assert "Capítulo falso" in cerebro.secao(nota["_corpo"], "Descrição do vídeo")  # "##" da descrição não virou seção


def test_varrer_so_baixa_o_que_e_novo(mundo):
    rodar("importar", "canal-x")
    mundo["baixados"].clear()
    _, saida = rodar("varrer")
    assert saida["canal-x"]["novos"] == [] and mundo["baixados"] == []
    mundo["acervo"].insert(0, video("v4", "2026-09-19"))
    _, saida = rodar("varrer")
    assert [v["id"] for v in saida["canal-x"]["novos"]] == ["v4"] and mundo["baixados"] == ["v4"]
    assert json.loads(cerebro.ESTADO.read_text(encoding="utf-8"))["canais"]["canal-x"]["ultimo_video"]["id"] == "v4"


def test_importar_com_limite_continua_de_onde_parou(mundo):
    _, saida = rodar("importar", "canal-x", "--limite", "2")
    assert len(saida["canal-x"]["novos"]) == 2 and saida["canal-x"]["restam"] == 1
    _, saida = rodar("importar", "canal-x", "--limite", "2")
    assert [v["id"] for v in saida["canal-x"]["novos"]] == ["v1"] and saida["canal-x"]["restam"] == 0


def test_importar_desde_corta_o_que_e_antigo(mundo):
    _, saida = rodar("importar", "canal-x", "--desde", "2026-06-01")
    assert [v["id"] for v in saida["canal-x"]["novos"]] == ["v3", "v2"]
    assert mundo["baixados"] == ["v3", "v2", "v1"][:3] and len(cerebro.notas()) == 2


def test_video_recente_sem_legenda_espera_e_antigo_e_descartado(mundo):
    ontem = (date.today() - timedelta(days=1)).isoformat()
    mundo["falhas"] = {"v3": cerebro.SemLegenda("sem legenda", ontem), "v1": cerebro.SemLegenda("sem legenda", "2026-01-15")}
    _, saida = rodar("importar", "canal-x")
    assert [v["id"] for v in saida["canal-x"]["aguardando"]] == ["v3"] and [v["id"] for v in saida["canal-x"]["descartados"]] == ["v1"]
    mundo["falhas"], mundo["baixados"] = {}, []
    _, saida = rodar("varrer")
    assert [v["id"] for v in saida["canal-x"]["novos"]] == ["v3"] and mundo["baixados"] == ["v3"]  # v1 descartado não volta
    assert json.loads(cerebro.ESTADO.read_text(encoding="utf-8"))["canais"]["canal-x"]["aguardando"] == {}
    _, saida = rodar("importar", "canal-x", "--video", "v1")  # pedido explícito tira do descarte
    assert [v["id"] for v in saida["canal-x"]["novos"]] == ["v1"]


def test_limite_de_taxa_interrompe_sem_perder_o_que_ja_entrou(mundo):
    mundo["falhas"] = {"v2": cerebro.LimiteDeTaxa("HTTP Error 429")}
    _, saida = rodar("importar", "canal-x")
    assert [v["id"] for v in saida["canal-x"]["novos"]] == ["v3"] and "429" in saida["canal-x"]["interrompido"] and saida["canal-x"]["restam"] == 2
    assert json.loads(cerebro.ESTADO.read_text(encoding="utf-8"))["canais"]["canal-x"]["descartados"] == {}


def test_varrer_avisa_quando_o_canal_nunca_foi_importado(mundo):
    _, saida = rodar("varrer", "--ultimos", "2")
    assert "importar canal-x" in saida["canal-x"]["aviso"]


def test_canal_pausado_fica_fora_da_varredura(mundo):
    rodar("canal", "pausar", "canal-x")
    assert rodar("varrer")[1] == {}


def test_canal_add_recusa_duplicado(mundo):
    with pytest.raises(SystemExit, match="já está cadastrado"):
        cerebro.main(["canal", "add", "https://www.youtube.com/@outro-endereco-do-mesmo-canal"])


def test_validar_exige_nota_destilada_completa(mundo):
    rodar("importar", "canal-x")
    assert rodar("validar")[0] == 0  # nota bruta é válida
    a, b, c = cerebro.notas()
    destilar(a, temas='["miniatura", "shorts"]')       # o formato que o script grava; YAML solto tem teste próprio
    destilar(b, temas='["inventado"]', corpo=False)
    destilar(c, relevancia="fora", temas="[]")
    codigo, saida = rodar("validar")
    erros = "\n".join(saida["erros"])
    assert codigo == 1 and a["_arquivo"].name not in erros and c["_arquivo"].name not in erros
    assert "tema fora de" in erros and "seção 'Boas práticas' não foi escrita" in erros
    assert cerebro.notas()[0]["temas"] == ["miniatura", "shorts"]


def test_buscar_e_indice_so_enxergam_o_que_foi_destilado_e_serve(mundo):
    rodar("importar", "canal-x")
    a, b, c = cerebro.notas()
    destilar(a)
    destilar(b, relevancia="fora", temas="[]")
    _, achadas = rodar("buscar", "--tema", "miniatura", "--praticas")
    assert [n["id"] for n in achadas] == [a["id"]] and "Abra com a promessa" in achadas[0]["praticas"]
    assert rodar("pendentes")[1]["total"] == 1
    rodar("indice")
    indice = cerebro.INDICE.read_text(encoding="utf-8")
    assert "## Miniatura (`miniatura`)" in indice and a["titulo"] in indice and "## Shorts" not in indice
    with pytest.raises(SystemExit, match="não existe"):
        cerebro.main(["buscar", "--tema", "nao-existe"])


def test_blocos_da_legenda_agrupa_por_tempo_e_limpa_ruido():
    eventos = [{"tStartMs": 0, "segs": [{"utf8": "Primeira"}, {"utf8": " frase."}]}, {"tStartMs": 1000, "segs": [{"utf8": "\n"}]},
               {"tStartMs": 20000, "segs": [{"utf8": "[Music] segue"}]}, {"tStartMs": 50000, "segs": [{"utf8": "e fecha."}]},
               {"tStartMs": 61000, "segs": [{"utf8": "Outro bloco"}]}, {"tStartMs": 62000}]
    assert cerebro.blocos_da_legenda(eventos) == [(0, "Primeira frase. segue e fecha."), (61, "Outro bloco")]


def test_escolher_legenda_prefere_manual_e_nunca_traducao_de_maquina():
    auto = {"en-orig": ["a"], "en": ["b"], "pt": ["traduzida"]}
    assert cerebro.escolher_legenda({"language": "en-US", "subtitles": {"en": ["m"]}, "automatic_captions": auto}) == (["m"], "manual", "en")
    assert cerebro.escolher_legenda({"language": "en-US", "automatic_captions": auto}) == (["a"], "automatica", "en")
    assert cerebro.escolher_legenda({"automatic_captions": {"pt-orig": ["o"], "en": ["t"]}}) == (["o"], "automatica", "pt")  # idioma vem do -orig
    assert cerebro.escolher_legenda({"automatic_captions": {"pt": ["p"]}}, "pt") == (["p"], "automatica", "pt")          # senão, do canal
    with pytest.raises(cerebro.SemLegenda):
        cerebro.escolher_legenda({"language": "pt", "automatic_captions": {"en": ["t"]}})


# ---------- achados da revisão de 19/09/2026 ----------

def estado_de(canal="canal-x"):
    return json.loads(cerebro.ESTADO.read_text(encoding="utf-8"))["canais"][canal]


def test_erro_passageiro_nunca_descarta_e_rede_caida_para_a_rodada(mundo):
    mundo["falhas"] = {"v2": cerebro.Passageiro("timed out")}
    codigo, saida = rodar("importar", "canal-x")
    assert [v["id"] for v in saida["canal-x"]["novos"]] == ["v3", "v1"] and saida["canal-x"]["descartados"] == [] and codigo == 0
    assert list(estado_de()["aguardando"]) == ["v2"]
    mundo["falhas"] = {}
    assert [v["id"] for v in rodar("importar", "canal-x")[1]["canal-x"]["novos"]] == ["v2"]  # voltou sozinho

    mundo["acervo"][:0] = [video(f"n{i}", "2026-09-19") for i in range(5)]
    mundo["falhas"], mundo["baixados"] = {f"n{i}": cerebro.Passageiro("Network is unreachable") for i in range(5)}, []
    codigo, saida = rodar("importar", "canal-x")
    assert codigo == 2 and "falhas de rede seguidas" in saida["canal-x"]["interrompido"] and len(mundo["baixados"]) == cerebro.FALHAS_SEGUIDAS
    assert estado_de()["descartados"] == {} and saida["canal-x"]["restam"] == 2


def test_erro_definitivo_descarta(mundo):
    mundo["falhas"] = {"v2": cerebro.Indisponivel("Private video")}
    _, saida = rodar("importar", "canal-x")
    assert [v["id"] for v in saida["canal-x"]["descartados"]] == ["v2"] and "v2" in estado_de()["descartados"]


def test_quem_espera_volta_mesmo_fora_dos_ultimos_do_canal(mundo):
    mundo["falhas"] = {"v1": cerebro.Passageiro("timed out")}
    rodar("importar", "canal-x")
    mundo["falhas"] = {}
    _, saida = rodar("varrer", "--ultimos", "2")  # v1 é o terceiro da lista
    assert [v["id"] for v in saida["canal-x"]["novos"]] == ["v1"] and estado_de()["aguardando"] == {}


def test_corte_desde_fica_no_canal_e_vale_para_o_varrer(mundo):
    rodar("importar", "canal-x", "--desde", "2026-06-01")
    assert cerebro.carregar_canais()[0]["desde"] == "2026-06-01"
    mundo["baixados"].clear()
    _, saida = rodar("varrer")
    assert saida["canal-x"]["novos"] == [] and mundo["baixados"] == [] and "aviso" not in saida["canal-x"]  # v1 não volta nem é baixado de novo
    _, saida = rodar("importar", "canal-x", "--desde", "tudo")  # mudar o corte libera o que ele tinha barrado
    assert [v["id"] for v in saida["canal-x"]["novos"]] == ["v1"] and cerebro.carregar_canais()[0]["desde"] is None


def test_nota_quebrada_nao_derruba_a_rotina_e_o_validar_aponta(mundo, capsys):
    rodar("importar", "canal-x")
    (cerebro.VIDEOS / "canal-x" / "rascunho.md").write_text("sem frontmatter nenhum", encoding="utf-8")
    (cerebro.VIDEOS / "canal-x" / "vazio.md").write_text("", encoding="utf-8")
    for comando in (["status"], ["pendentes"], ["varrer"], ["buscar", "--tema", "miniatura"], ["indice"]):
        assert rodar(*comando)[0] == 0
    assert "pulei" in capsys.readouterr().err
    codigo, saida = rodar("validar")
    assert codigo == 1 and any(e.startswith("cerebro/videos/canal-x/rascunho.md: sem frontmatter") for e in saida["erros"])


def test_frontmatter_editado_a_mao(mundo):
    rodar("importar", "canal-x")
    a, b, c = cerebro.notas()
    destilar(a, temas='["miniatura"]      # só ids de temas.json')
    texto = a["_arquivo"].read_text(encoding="utf-8").replace("status: destilado", 'status: "destilado"     # bruto -> destilado')
    a["_arquivo"].write_text(texto.replace("\n", "\r\n"), encoding="utf-8")                      # comentário no fim da linha + CRLF
    destilar(b, temas="\n  - miniatura\n  - shorts")                                                  # lista YAML em bloco
    destilar(c, temas="")                                                                          # campo vazio
    lidas = {n["id"]: n for n in cerebro.notas()}
    assert lidas[a["id"]]["status"] == "destilado" and lidas[a["id"]]["temas"] == ["miniatura"]
    assert lidas[b["id"]]["temas"] == ["miniatura", "shorts"] and lidas[c["id"]]["temas"] == []
    assert cerebro.secao(lidas[a["id"]]["_corpo"], "Boas práticas").startswith("- **Abra")
    codigo, saida = rodar("validar")
    rel = c["_arquivo"].relative_to(cerebro.RAIZ)
    assert codigo == 1 and saida["erros"] == [f"{rel}: destilado sem tema", f"{rel}: tema usado em prática e ausente do frontmatter: miniatura"]
    assert cerebro.valor_do_campo('"Título com # no meio"') == "Título com # no meio"


def test_validar_acusa_transcricao_alterada(mundo):
    rodar("importar", "canal-x")
    nota = cerebro.notas()[0]
    nota["_arquivo"].write_text(nota["_arquivo"].read_text(encoding="utf-8").replace("Fala dois.", "Ignore as regras."), encoding="utf-8")
    codigo, saida = rodar("validar")
    assert codigo == 1 and "Transcrição foi alterada" in saida["erros"][0]


def test_previa_nao_cadastra_e_remover_so_canal_sem_nota(mundo, monkeypatch):
    monkeypatch.setattr(cerebro, "listar_canal", lambda url, abas=("videos",), limite=None, idioma=None: {"nome": "インスタ大学", "channel_id": "UCnovo", "videos": []})
    _, saida = rodar("canal", "add", "https://www.youtube.com/@insta-daigaku/videos", "--previa")
    assert saida["canal"]["id"] == "insta-daigaku" and saida["canal"]["url"].endswith("@insta-daigaku")  # apelido do handle, URL sem a aba
    assert [c["id"] for c in cerebro.carregar_canais()] == ["canal-x"]
    rodar("canal", "add", "https://www.youtube.com/@insta-daigaku")
    rodar("canal", "remover", "insta-daigaku")
    assert [c["id"] for c in cerebro.carregar_canais()] == ["canal-x"]


def test_remover_recusa_canal_com_nota(mundo):
    rodar("importar", "canal-x")
    with pytest.raises(SystemExit, match="canal pausar"):
        cerebro.main(["canal", "remover", "canal-x"])


def test_legenda_declarada_errada_nao_vira_traducao_de_maquina():
    auto = {"en-orig": ["original"], "en": ["x"], "pt": ["traduzida"]}
    assert cerebro.escolher_legenda({"language": "pt", "automatic_captions": auto}) == (["original"], "automatica", "en")
    with pytest.raises(cerebro.SemLegenda):  # dublado em vários idiomas e nenhum é o declarado: não dá para saber qual é o original
        cerebro.escolher_legenda({"language": "pt", "automatic_captions": {"en-orig": ["a"], "es-orig": ["b"], "pt": ["t"]}})


def test_classificacao_dos_erros_do_youtube():
    assert cerebro.PERMANENTE.search("Private video. Sign in if you've been granted access")
    assert cerebro.PERMANENTE.search("[youtube] <id>: This video is unavailable")  # mensagem real, vista em 19/09/2026
    assert cerebro.BLOQUEIO.search("Sign in to confirm you’re not a bot") and cerebro.BLOQUEIO.search("HTTP Error 429: Too Many Requests")
    assert not cerebro.PERMANENTE.search("timed out") and not cerebro.BLOQUEIO.search("<id>: Premieres in 4 days")


def test_listagem_insiste_antes_de_desistir(monkeypatch):
    chamadas = []

    class Falso:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def extract_info(self, url, download):
            chamadas.append(url)
            if len(chamadas) < 3:
                raise RuntimeError("Failed to resolve url (does the playlist exist?)")  # falha real e passageira do YouTube
            return {"channel": "Canal", "channel_id": "UC1", "entries": [{"id": "a", "title": "A", "duration": 10}]}

    monkeypatch.setattr(cerebro, "_ydl", lambda **_: Falso())
    monkeypatch.setattr(cerebro.time, "sleep", lambda _: None)
    assert [v["id"] for v in cerebro.listar_canal("https://www.youtube.com/@canal/videos")["videos"]] == ["a"]
    assert chamadas == ["https://www.youtube.com/@canal/videos"] * 3  # e a aba não foi duplicada na URL
    chamadas.clear()
    monkeypatch.setattr(Falso, "extract_info", lambda self, url, download: (_ for _ in ()).throw(RuntimeError("HTTP Error 429: Too Many Requests")))
    with pytest.raises(cerebro.LimiteDeTaxa):
        cerebro.listar_canal("https://www.youtube.com/@canal")


def test_bloqueio_do_youtube_espera_e_insiste_antes_de_largar(mundo, monkeypatch):
    esperas, bloqueios = [], {"restam": 2}
    original = cerebro.baixar_video

    def baixar(vid, idioma=None):
        if vid == "v2" and bloqueios["restam"]:
            bloqueios["restam"] -= 1
            raise cerebro.LimiteDeTaxa("Sign in to confirm you're not a bot")
        return original(vid, idioma)

    monkeypatch.setattr(cerebro, "baixar_video", baixar)
    monkeypatch.setattr(cerebro.time, "sleep", esperas.append)
    codigo, saida = rodar("importar", "canal-x")
    assert codigo == 0 and [v["id"] for v in saida["canal-x"]["novos"]] == ["v3", "v2", "v1"]
    assert [e for e in esperas if e >= 90] == [90, 180]  # recuou duas vezes e seguiu


def test_tema_marcado_na_pratica_tem_que_estar_no_frontmatter(mundo):
    rodar("importar", "canal-x")
    nota = cerebro.notas()[0]
    destilar(nota)
    texto = nota["_arquivo"].read_text(encoding="utf-8")
    nota["_arquivo"].write_text(texto.replace("`[miniatura]` `[01:05]`", "[shorts] [inventado] [01:05]"), encoding="utf-8")
    erros = "\n".join(rodar("validar")[1]["erros"])
    assert "ausente do frontmatter: shorts" in erros and "marcado em prática: inventado" in erros and "01:05" not in erros


def test_lista_de_temas_sem_aspas_vira_lista_e_o_validar_pede_o_formato_do_script(mundo):
    """`temas: [a, b]` chega como texto em quem só faz json.loads: iterado, vira um item por letra."""
    rodar("importar", "canal-x")
    nota = cerebro.notas()[0]
    destilar(nota, temas="[miniatura, shorts]")
    lida = cerebro.notas()[0]
    assert lida["temas"] == ["miniatura", "shorts"]                       # ler_cabeca entende, ninguém vê letra avulsa
    erros = rodar("validar")[1]["erros"]
    assert erros == [f'{nota["_arquivo"].relative_to(cerebro.RAIZ)}: a linha `temas` não está no JSON que o '
                     'script grava. Escreva: temas: ["miniatura", "shorts"]']
    nota["_arquivo"].write_text(nota["_arquivo"].read_text(encoding="utf-8").replace("temas: [miniatura, shorts]",
                                                                                     'temas: ["miniatura", "shorts"]'), encoding="utf-8")
    assert rodar("validar")[0] == 0


RAIZ_REAL = Path(__file__).resolve().parents[1]


def test_taxonomia_real_e_de_youtube():
    temas = json.loads((RAIZ_REAL / "cerebro" / "temas.json").read_text(encoding="utf-8"))["temas"]
    ids = [t["id"] for t in temas]
    assert len(ids) >= 14 and len(set(ids)) == len(ids)
    assert {"miniatura", "titulo", "retencao", "shorts", "algoritmo"} <= set(ids)
    assert not {"carrossel", "reels", "stories", "hashtags"} & set(ids)
    assert all(t.get("nome") and t.get("cobre") for t in temas)
    import re
    assert all(re.fullmatch(r"[a-z][a-z-]+", i) for i in ids)


def test_validar_e_buscar_na_raiz_real():
    import subprocess
    r = subprocess.run([sys.executable, "cerebro.py", "validar"], cwd=RAIZ_REAL, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert subprocess.run([sys.executable, "cerebro.py", "buscar", "--tema", "miniatura", "--json"], cwd=RAIZ_REAL, capture_output=True).returncode == 0
    r = subprocess.run([sys.executable, "cerebro.py", "buscar", "--tema", "carrossel"], cwd=RAIZ_REAL, capture_output=True, text=True)
    assert r.returncode != 0 and "não existe" in r.stderr
    assert (RAIZ_REAL / "cerebro" / "README.md").exists()


def test_descoberta_do_cerebro_esta_configurada_na_raiz_real():
    """`cerebro.py descobrir` só roda se cerebro/descoberta.json existir com consultas: é o que o /cerebro-descobrir usa (D-45)."""
    cfg = cerebro.descoberta_config()
    assert len(cfg["consultas"]) >= 5 and {c["idioma"] for c in cfg["consultas"]} == {"pt", "en"}
    assert cfg["palavras_do_tema"] and "youtube" in cfg["palavras_do_tema"]
    assert 1 <= cfg["max_canais_por_rodada"] <= 3 and cfg["fatia_minima"] >= 0.5
