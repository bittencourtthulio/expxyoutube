"""Front do painel: arquivos reais servidos pelo servidor, nove abas, token e sintaxe JS válida."""
import re
import shutil
import subprocess
import threading
import urllib.request
from pathlib import Path

import pytest

import painel

PASTA = Path(painel.__file__).resolve().parent / "painel"
ABAS = ("painel", "escritorio", "reuniao", "tarefas", "relatorios", "decisoes", "conhecimento", "grafo", "apresentacoes")


@pytest.fixture
def url():
    srv = painel.servidor(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def estaticos():
    return sorted(p.name for p in PASTA.glob("*") if p.suffix in (".js", ".css"))


def test_index_tem_as_nove_abas_e_o_marcador_do_token():
    html = (PASTA / "index.html").read_text(encoding="utf-8")
    assert "__TOKEN__" in html
    assert [a for a in re.findall(r'<button role="tab" data-aba="([a-z]+)"', html)] == list(ABAS)
    modulos = {"escritorio.js", "grafo.js"}  # carregados por import() sob demanda, não por <script>
    for arq in estaticos():
        assert f"/estatico/{arq}" in html or arq in modulos, arq


def test_estaticos_servidos(url):
    assert {"base.css", "dashboard.css", "dashboard.js"} <= set(estaticos())
    for arq in estaticos():
        with urllib.request.urlopen(f"{url}/estatico/{arq}", timeout=5) as r:
            assert r.status == 200
    with urllib.request.urlopen(url + "/", timeout=5) as r:
        assert painel.TOKEN in r.read().decode()


@pytest.mark.skipif(not shutil.which("node"), reason="node ausente")
def test_js_com_sintaxe_valida():
    for js in PASTA.glob("*.js"):
        texto = js.read_text(encoding="utf-8")
        modulo = bool(re.search(r"^(import|export) ", texto, flags=re.M))
        cmd = ["node", "--check", "--input-type=module", "-"] if modulo else ["node", "--check", "-"]
        r = subprocess.run(cmd, input=texto, capture_output=True, text=True)
        assert r.returncode == 0, f"{js.name}: {r.stderr}"
    html = (PASTA / "index.html").read_text(encoding="utf-8")
    inline = re.findall(r"<script>(.*?)</script>", html, flags=re.S)
    assert inline
    r = subprocess.run(["node", "--check", "--input-type=commonjs", "-"], input="\n".join(inline), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_tema_vermelho():
    css = (PASTA / "base.css").read_text(encoding="utf-8")
    assert "--marca: #EF4444" in css and "--bom: #4ADE80" in css and "--perigo: #FB923C" in css
    assert "34,197,94" not in css and "#22C55E" not in css


def test_abas_da_sprint_04_tem_arquivo(url):
    for arq in ("reuniao.js", "tarefas.js", "relatorios.js", "decisoes.js", "conhecimento.js", "reuniao.css", "tarefas.css", "relatorios.css"):
        with urllib.request.urlopen(f"{url}/estatico/{arq}", timeout=5) as r:
            assert r.status == 200, arq


def test_escritorio_e_grafo_servidos(url):
    for arq in ("escritorio.js", "grafo.js", "sala3d.js", "sala3d.css", "vendor/three.module.min.js"):
        with urllib.request.urlopen(f"{url}/estatico/{arq}", timeout=10) as r:
            assert r.status == 200, arq
    for arq in ("escritorio.js", "grafo.js"):
        texto = (PASTA / arq).read_text(encoding="utf-8")
        assert "./vendor/three.module.min.js" in texto and "22c55e" not in texto.lower() and "copywriter" not in texto


def test_aba_apresentacoes_fala_com_as_rotas_e_respeita_o_corte_80():
    js = (PASTA / "apresentacoes.js").read_text(encoding="utf-8")
    for trecho in ("/api/apresentacoes", "/api/apresentacao/status", "/apresentacao/", "palco.html", "capa.png", ">= 80", '"ok"', '"aviso"', "gravada"):
        assert trecho in js, trecho
    assert "#EF4444" not in js and "perigo" not in js
    html = (PASTA / "index.html").read_text(encoding="utf-8")
    assert "/estatico/apresentacoes.js" in html and "/estatico/apresentacoes.css" in html and "abreApresentacoes" in html
