"""Projeto Remotion das apresentações: versões fixas, sem Player nem licenseKey, tsc quando instalado, cenas e render.mjs."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
MOTION = RAIZ / "apresentacoes" / "motion"
SRC = MOTION / "src"
NODE_MODULES = MOTION / "node_modules"
VERSAO = "4.0.522"


def fontes_ts():
    return list(SRC.rglob("*.ts")) + list(SRC.rglob("*.tsx")) + list((MOTION / "scripts").glob("*.mjs"))


def test_pacotes_remotion_na_mesma_versao_sem_player():
    pkg = json.loads((MOTION / "package.json").read_text())
    deps = {**pkg["dependencies"], **pkg.get("devDependencies", {})}
    remotion = {k: v for k, v in deps.items() if k == "remotion" or k.startswith("@remotion/")}
    assert {"remotion", "@remotion/cli", "@remotion/bundler", "@remotion/renderer", "@remotion/google-fonts", "@remotion/layout-utils"} <= set(remotion)
    assert set(remotion.values()) == {VERSAO}, remotion
    assert "@remotion/player" not in deps
    assert deps["react"] == "18.3.1" and deps["react-dom"] == "18.3.1"
    assert ".env" not in json.dumps(pkg.get("scripts", {}))


def test_sem_license_key_e_root_por_input_props():
    for arq in fontes_ts():
        assert "licenseKey" not in arq.read_text(encoding="utf-8"), arq.name
    root = (SRC / "Root.tsx").read_text(encoding="utf-8")
    assert "getInputProps" in root and 'id={`slide-${' in root
    deck_ts = (SRC / "deck.ts").read_text(encoding="utf-8")
    assert "LARGURA = 1920" in deck_ts and "ALTURA = 1080" in deck_ts and "FRAMES_POR_SLIDE = 240" in deck_ts and "FPS = 30" in deck_ts
    assert "FRAMES_POR_SLIDE" in root and "LARGURA" in root and "ALTURA" in root
    assert "aplicarMarca" in root and "aplicarMarca" in (SRC / "theme.ts").read_text(encoding="utf-8")
    assert (SRC / "index.ts").read_text(encoding="utf-8").count("registerRoot(") == 1


@pytest.mark.skipif(not NODE_MODULES.is_dir() or not shutil.which("node"), reason="node_modules ausente: tsc só roda instalado (D-42)")
def test_tsc_sem_erros():
    r = subprocess.run(["node", str(NODE_MODULES / "typescript" / "bin" / "tsc"), "--noEmit", "-p", str(MOTION)],
                       capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


def test_componentes_portados_para_16_9():
    comp = SRC / "components"
    for nome in ("Entrance.tsx", "Stagger.tsx", "WordReveal.tsx", "KenBurns.tsx", "Layers.tsx", "Timeline.ts", "Counter.tsx"):
        assert (comp / nome).exists(), nome
    layers = (comp / "Layers.tsx").read_text(encoding="utf-8")
    assert "useVideoConfig" in layers and not re.search(r"\b(1200|900)\b", layers)
    stagger = (comp / "Stagger.tsx").read_text(encoding="utf-8")
    assert "variant" in stagger and "variantFor" in stagger
    for arq in comp.iterdir():
        texto = arq.read_text(encoding="utf-8")
        assert "extrapolateLeft" not in texto or "clamp" in texto, arq.name
        # interpolação sobre frames sempre com easing (regra 1); sobre o progresso de um spring já é curva
        assert "interpolate(frame" not in texto or "easing" in texto, arq.name


CENAS = ("Titulo", "Declaracao", "Grade", "Comparacao", "Etapas", "Estatisticas", "Fluxo", "Screenshot", "Cta")


def test_oito_cenas_mapeadas_sem_exit_e_com_pilha():
    scenes = SRC / "scenes"
    root = (SRC / "Root.tsx").read_text(encoding="utf-8")
    for nome in CENAS:
        assert (scenes / f"{nome}.tsx").exists(), nome
        assert nome in root, f"Root não mapeia {nome}"
    for arq in scenes.glob("*.tsx"):
        assert "useExit" not in arq.read_text(encoding="utf-8"), arq.name
    slide = (scenes / "Slide.tsx").read_text(encoding="utf-8")
    assert "BgMesh" in slide and "Finish" in slide and "padStart(2" in slide and "breathe" in slide
    for nome in ("Screenshot", "Cta"):
        texto = (scenes / f"{nome}.tsx").read_text(encoding="utf-8")
        assert "imagem ?" in texto or "imagem &&" in texto or "imagem !== null" in texto or "imagem != null" in texto, nome
    assert "CANAL_ACCENT" in (scenes / "Cta.tsx").read_text(encoding="utf-8")


def test_render_mjs_um_bundle_sem_license_e_mesma_linha_de_comando():
    texto = (MOTION / "scripts" / "render.mjs").read_text(encoding="utf-8")
    assert texto.count("bundle(") == 1 and "licenseKey" not in texto
    assert "ensureBrowser" in texto and "selectComposition" in texto and "renderMedia" in texto and "renderStill" in texto
    assert "process.argv" in texto and "slide ${" in texto
    falso = (RAIZ / "tests" / "node_falso.py").read_text(encoding="utf-8")
    assert "sys.argv[1:5]" in falso  # script deck saida ativos: a mesma linha de comando
