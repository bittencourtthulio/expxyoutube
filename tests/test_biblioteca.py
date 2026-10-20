"""biblioteca.py: o motor do cerebro.py sobre outra base. Ingestão é coberta em test_cerebro.py; aqui, o que muda. Sem rede."""
import io
import json
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

import biblioteca
import cerebro as motor

RAIZ = Path(__file__).parents[1]
CANAL = {"id": "canal-x", "nome": "Canal X", "url": "https://www.youtube.com/@canalx", "channel_id": "UCx", "abas": ["videos"], "ativo": True}
IDEIA = "- **Os 3 arquivos que o agente lê antes do seu código.** Mostra o que configurar, para o líder técnico. Cabe em: video-longo. [agentes] [01:05]"


def video(vid, dia):
    return {"id": vid, "titulo": f"Vídeo {vid}", "publicado_em": dia, "duracao_seg": 600, "idioma": "en", "legenda": "automatica",
            "visualizacoes": 1000, "descricao": "", "capitulos": [], "blocos": [(0, "Fala um."), (65, "Fala dois.")]}


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    """A base da biblioteca num diretório temporário; o monkeypatch devolve o motor à base do cérebro no fim."""
    acervo = [video("v2", "2026-09-10"), video("v1", "2026-08-01")]
    for nome, valor in {**motor.globais_da_base(biblioteca.BASE, tmp_path), "RAIZ": tmp_path}.items():
        monkeypatch.setattr(motor, nome, valor)
    monkeypatch.setattr(motor, "usar_base", lambda base: None)  # o `main` da biblioteca não pode desfazer o tmp_path
    monkeypatch.setattr(motor, "listar_canal", lambda url, abas=("videos",), limite=None, idioma=None: {
        "nome": "Canal X", "channel_id": "UCx", "videos": [{"id": v["id"], "titulo": v["titulo"], "duracao_seg": 600, "aba": "videos"} for v in acervo[:limite]]})
    monkeypatch.setattr(motor, "baixar_video", lambda vid, idioma=None: next(v for v in acervo if v["id"] == vid))
    monkeypatch.setattr(motor.time, "sleep", lambda _: None)
    motor.salvar_canais([dict(CANAL)])
    motor.gravar_json(motor.TEMAS, {"temas": [{"id": "agentes", "nome": "Agentes"}, {"id": "modelos", "nome": "Modelos"}]})
    return tmp_path


def rodar(*argv):
    saida = io.StringIO()
    with redirect_stdout(saida):
        codigo = biblioteca.main([*argv, "--json"])
    return codigo, json.loads(saida.getvalue())


def destilar(nota, ideia=IDEIA, temas='["agentes"]'):
    texto = nota["_arquivo"].read_text(encoding="utf-8")
    texto = texto.replace('status: "bruto"', 'status: "destilado"').replace("relevancia: null", 'relevancia: "alta"')
    texto = texto.replace("temas: []", f"temas: {temas}").replace("destilado_em: null", 'destilado_em: "2026-09-19"')
    nota["_arquivo"].write_text(texto.replace(motor.PENDENTE, ideia), encoding="utf-8")


def test_base_da_biblioteca_nao_encosta_na_do_cerebro(mundo):
    rodar("importar", "canal-x")
    assert sorted(p.name for p in mundo.iterdir()) == ["biblioteca", "estado"]
    assert [p.name for p in (mundo / "estado").iterdir()] == ["biblioteca.json"]
    assert len(list((mundo / "biblioteca" / "videos" / "canal-x").glob("*.md"))) == 2
    assert "biblioteca.py canal add" in json.loads((mundo / "biblioteca" / "canais.json").read_text(encoding="utf-8"))["_"]


def test_nota_nasce_com_a_secao_de_ideias(mundo):
    rodar("importar", "canal-x")
    corpo = motor.notas("canal-x")[0]["_corpo"]
    assert motor.secao(corpo, "Ideias de conteúdo") == motor.PENDENTE and "## Boas práticas" not in corpo


def test_buscar_traz_ideias_por_tema_e_por_serie(mundo):
    rodar("importar", "canal-x")
    destilar(motor.notas("canal-x")[0])
    _, achadas = rodar("buscar", "--tema", "agentes", "--ideias")
    assert len(achadas) == 1 and achadas[0]["ideias"] == IDEIA and "praticas" not in achadas[0]
    assert len(rodar("buscar", "--texto", "cabe em: video-longo")[1]) == 1  # a pauta de uma série se acha pelo texto
    assert rodar("buscar", "--tema", "modelos")[1] == []
    with pytest.raises(SystemExit):
        rodar("buscar", "--tema", "gancho")  # tema do cérebro não existe aqui
    with pytest.raises(SystemExit):
        rodar("buscar", "--tema", "agentes", "--praticas")  # a opção do cérebro também não


def test_validar_cobra_a_secao_de_ideias_e_o_tema_da_ideia(mundo):
    rodar("importar", "canal-x")
    a, b = motor.notas("canal-x")
    destilar(a, ideia=IDEIA.replace("[agentes]", "[modelos] [inventado]"))
    texto = b["_arquivo"].read_text(encoding="utf-8")  # frontmatter destilado, seções ainda pendentes
    b["_arquivo"].write_text(texto.replace('status: "bruto"', 'status: "destilado"').replace("relevancia: null", 'relevancia: "media"')
                             .replace("temas: []", 'temas: ["agentes"]').replace("destilado_em: null", 'destilado_em: "2026-09-19"'), encoding="utf-8")
    codigo, saida = rodar("validar")
    erros = "\n".join(saida["erros"])
    assert codigo == 1 and "seção 'Ideias de conteúdo' não foi escrita" in erros
    assert "tema usado em ideia e ausente do frontmatter: modelos" in erros and "biblioteca/temas.json marcado em ideia: inventado" in erros
    assert "01:05" not in erros and "video-longo" not in erros  # minuto e `Cabe em:` não são tema


def test_indice_fala_da_biblioteca(mundo):
    rodar("importar", "canal-x")
    destilar(motor.notas("canal-x")[0])
    rodar("indice")
    indice = (mundo / "biblioteca" / "INDEX.md").read_text(encoding="utf-8")
    assert indice.startswith("# Biblioteca de pautas: índice") and "biblioteca.py buscar --tema <tema> --ideias" in indice
    assert "## Agentes (`agentes`)" in indice and "](videos/canal-x/" in indice


def test_cli_de_verdade_troca_de_base():
    """Sem fixture: o processo do biblioteca.py enxerga a base dele e o do cerebro.py continua na dele."""
    for script, tema_de_fora in (("biblioteca.py", "gancho"), ("cerebro.py", "agentes")):
        r = subprocess.run([sys.executable, str(RAIZ / script), "buscar", "--tema", tema_de_fora], text=True, capture_output=True)
        assert r.returncode != 0 and f"tema '{tema_de_fora}' não existe" in r.stderr
    ajuda = subprocess.run([sys.executable, str(RAIZ / "biblioteca.py"), "buscar", "--help"], text=True, capture_output=True).stdout
    assert "--ideias" in ajuda and "--praticas" not in ajuda


def test_temas_da_biblioteca_sao_validos():
    temas = json.loads((RAIZ / "biblioteca" / "temas.json").read_text(encoding="utf-8"))["temas"]
    ids = [t["id"] for t in temas]
    assert len(ids) == len(set(ids)) and all(t["nome"] and t["cobre"] for t in temas)
    assert all(motor.re.fullmatch(r"[a-z][a-z-]+", i) for i in ids)  # é o formato que o `validar` reconhece como marcador de tema


# ---------- descoberta de canal novo ----------
def _busca(canais):
    """canais: {channel_id: (nome, [(video_id, visualizacoes, duracao_seg)])} -> resposta da busca do YouTube."""
    return lambda consulta, janela, limite, idioma=None: [
        {"id": vid, "titulo": f"{nome} {vid}", "visualizacoes": views, "duracao_seg": dur, "canal_nome": nome, "channel_id": cid}
        for cid, (nome, videos) in canais.items() for vid, views, dur in videos]


@pytest.fixture
def descoberta(mundo, monkeypatch):
    motor.gravar_json(motor.PASTA / "descoberta.json", {"consultas": [{"q": "IA para SaaS", "idioma": "pt"}], "janelas": ["ano"], "max_candidatos": 5,
                                                         "palavras_do_tema": ["ia", "saas"]})
    inscritos = {"nicho": 20_000, "grande": 900_000, "pequeno": 3_000, "portal": 19_000_000}
    monkeypatch.setattr(motor, "inscritos_do_canal", lambda vid: (inscritos[vid.split("-")[0]], "pt"))
    titulos = {"UCnicho": ["IA para SaaS: preço", "Agente de IA na software house", "Meu setup"], "UCgrande": ["IA no SaaS", "SaaS com IA", "IA vende"],
               "UCportal": ["Eleição", "Guerra", "IA vai acabar com tudo"]}
    monkeypatch.setattr(motor, "listar_canal", lambda url, abas=("videos",), limite=None, idioma=None: {
        "nome": url.rsplit("/", 1)[1], "channel_id": url.rsplit("/", 1)[1], "videos": [{"id": f"t{i}", "titulo": t} for i, t in enumerate(titulos[url.rsplit("/", 1)[1]])]})
    monkeypatch.setattr(motor, "buscar_no_youtube", _busca({
        "UCx": ("Canal X", [("x-1", 500_000, 600)]),                                  # já cadastrado: não é candidato
        "UCnicho": ("Nicho", [("nicho-1", 150_000, 900), ("nicho-2", 9_000, 700)]),   # canal pequeno, vídeo acima de 100 mil: passa pelo vídeo
        "UCgrande": ("Grande", [("grande-1", 40_000, 800)]),                           # vídeo fraco, canal acima de 100 mil: passa pelos inscritos
        "UCpequeno": ("Pequeno", [("pequeno-1", 60_000, 800)]),                        # nem um nem outro
        "UCportal": ("Portal", [("portal-1", 9_000_000, 1200)]),
        "UCshort": ("Short", [("short-1", 5_000_000, 40)])}))                          # short viral não diz nada sobre o canal
    return mundo


def test_descobrir_aplica_o_corte_numerico_e_entrega_os_titulos_para_o_julgamento(descoberta):
    codigo, r = rodar("descobrir")
    assert codigo == 0 and r["interrompido"] is None and r["ja_cadastrados"] == 1
    cand = {c["channel_id"]: c for c in r["candidatos"]}
    assert set(cand) == {"UCnicho", "UCgrande", "UCportal"}
    assert r["candidatos"][0]["channel_id"] == "UCnicho"                                  # dois vídeos na busca vence um vídeo gigante de portal
    assert cand["UCnicho"]["passou_por"] == ["video"] and cand["UCgrande"]["passou_por"] == ["inscritos"] and cand["UCportal"]["passou_por"] == ["video", "inscritos"]
    assert cand["UCnicho"]["video_gatilho"] == {"id": "nicho-1", "titulo": "Nicho nicho-1", "visualizacoes": 150_000}
    assert cand["UCnicho"]["fatia_por_palavras"] == 0.67 and cand["UCportal"]["fatia_por_palavras"] == 0.33 and len(cand["UCgrande"]["titulos"]) == 3
    assert r["desde_sugerido"] and motor.carregar_canais() == [CANAL]                     # descobrir nunca cadastra: só aponta
    estado = json.loads((descoberta / "estado" / "biblioteca-descoberta.json").read_text())
    assert estado["avaliados"]["UCpequeno"]["veredito"] == "recusado" and estado["avaliados"]["UCpequeno"]["por"] == "script" and "UCshort" not in estado["avaliados"]


def test_veredito_so_aprova_com_a_maior_parte_no_tema_e_candidato_julgado_nao_volta(descoberta):
    rodar("descobrir")
    with pytest.raises(SystemExit, match="não é a maior parte"):
        rodar("descobrir-veredito", "UCportal", "aprovado", "--no-tema", "1", "--lidos", "3", "--motivo", "viral")
    with pytest.raises(SystemExit, match="não é a maior parte"):
        rodar("descobrir-veredito", "UCgrande", "aprovado", "--no-tema", "15", "--lidos", "30", "--motivo", "metade não é maioria")
    with pytest.raises(SystemExit, match="não está entre os candidatos"):
        rodar("descobrir-veredito", "UCinventado", "aprovado", "--no-tema", "30", "--lidos", "30", "--motivo", "canal que não veio da busca")
    assert rodar("descobrir-veredito", "UCportal", "recusado", "--no-tema", "1", "--lidos", "3", "--motivo", "portal de notícia")[1]["veredito"] == "recusado"
    assert rodar("descobrir-veredito", "UCnicho", "aprovado", "--no-tema", "2", "--lidos", "3", "--motivo", "canal do assunto")[1]["veredito"] == "aprovado"
    assert [c["channel_id"] for c in rodar("descobrir")[1]["candidatos"]] == ["UCgrande"]   # só sobra quem ainda não foi julgado


def test_recusado_volta_a_ser_candidato_depois_da_validade_e_aprovado_nunca(descoberta):
    rodar("descobrir")
    rodar("descobrir-veredito", "UCportal", "recusado", "--no-tema", "1", "--lidos", "3", "--motivo", "portal")
    rodar("descobrir-veredito", "UCnicho", "aprovado", "--no-tema", "3", "--lidos", "3", "--motivo", "ok")
    arq = descoberta / "estado" / "biblioteca-descoberta.json"
    estado = json.loads(arq.read_text())
    for a in estado["avaliados"].values():
        a["quando"] = "2026-01-01"
    arq.write_text(json.dumps(estado))
    assert {c["channel_id"] for c in rodar("descobrir")[1]["candidatos"]} == {"UCportal", "UCgrande"}


def test_bloqueio_do_youtube_interrompe_com_codigo_2_e_nao_perde_o_que_ja_julgou(descoberta, monkeypatch):
    def bloqueado(*a, **k):
        raise motor.LimiteDeTaxa("HTTP Error 429")
    monkeypatch.setattr(motor, "inscritos_do_canal", bloqueado)
    codigo, r = rodar("descobrir")
    assert codigo == 2 and "bloqueio do YouTube" in r["interrompido"] and r["candidatos"] == []


def test_base_sem_descoberta_configurada_recusa_o_comando(mundo):
    with pytest.raises(SystemExit, match="não tem descoberta configurada"):
        rodar("descobrir")


def test_canais_do_territorio_sem_acervo():
    canais = json.loads((RAIZ / "biblioteca" / "canais.json").read_text(encoding="utf-8"))["canais"]
    assert canais == []  # A distribuição pública começa sem fontes operacionais.
    ids = {c["id"] for c in canais}
    for nota in (RAIZ / "biblioteca" / "videos").glob("*/*.md"):  # acervo do Instagram não vem junto (D-25)
        meta, _ = motor.ler_nota(nota)
        assert meta["canal"] in ids and meta["ingerido_em"] >= "2026-09-23", nota.name
    assert "Cabe em" in (RAIZ / "biblioteca" / "README.md").read_text(encoding="utf-8")
    assert "video-longo" in (RAIZ / "biblioteca" / "README.md").read_text(encoding="utf-8")
