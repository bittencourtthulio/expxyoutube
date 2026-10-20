"""Instalador: arquivo público, destino com espaços, falha de rede e proteção de dados existentes."""
import io
import os
import stat
import subprocess
import tarfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


def executavel(pasta, nome, texto):
    p = pasta / nome
    p.write_text(texto)
    p.chmod(0o755)
    return p


@pytest.fixture
def instalacao(tmp_path):
    binarios = tmp_path / "bin"
    binarios.mkdir()
    arquivo = tmp_path / "projeto.tar.gz"
    with tarfile.open(arquivo, "w:gz") as tar:
        for nome, texto in {".env.example": "TELEGRAM_YT_BOT_TOKEN=\n", "iniciar.sh": "#!/bin/bash\n", "requirements.txt": ""}.items():
            dados = texto.encode()
            info = tarfile.TarInfo("expxyoutube-main/" + nome)
            info.size = len(dados)
            tar.addfile(info, io.BytesIO(dados))
    executavel(binarios, "curl", '''#!/bin/bash
if [ "${TESTE_FALHA_DOWNLOAD:-}" = 1 ]; then exit 22; fi
while [ "$#" -gt 0 ]; do
  if [ "$1" = --output ]; then cp "$TESTE_ARQUIVO" "$2"; exit; fi
  shift
done
exit 1
''')
    executavel(binarios, "uv", '''#!/bin/bash
if [ "$1" = venv ]; then
  destino="${!#}"
  mkdir -p "$destino/bin"
  printf '#!/bin/bash\nexit 0\n' > "$destino/bin/python"
  chmod +x "$destino/bin/python"
fi
''')
    destino = tmp_path / "minha instalação"
    temporarios = tmp_path / "temporarios"
    temporarios.mkdir()
    env = {**os.environ, "PATH": str(binarios) + os.pathsep + os.environ["PATH"],
           "EXPXYOUTUBE_DIR": str(destino), "TMPDIR": str(temporarios), "TESTE_ARQUIVO": str(arquivo)}
    return destino, temporarios, env


def rodar(env):
    # Mesmo modo do comando público: script inteiro chega pela entrada padrão.
    return subprocess.run(["bash"], input=(RAIZ / "install.sh").read_text(), env=env,
                          capture_output=True, text=True, timeout=20)


def test_instala_em_pasta_com_espacos_e_env_privado(instalacao):
    destino, temporarios, env = instalacao
    r = rodar(env)
    assert r.returncode == 0, r.stderr
    assert (destino / ".env").read_text() == "TELEGRAM_YT_BOT_TOKEN=\n"
    assert stat.S_IMODE((destino / ".env").stat().st_mode) == 0o600
    assert (destino / "iniciar.sh").stat().st_mode & stat.S_IXUSR
    assert list(temporarios.iterdir()) == []


def test_reinstalacao_preserva_credenciais_e_arquivos(instalacao):
    destino, _, env = instalacao
    destino.mkdir()
    (destino / ".env").write_text("CONFIGURACAO_LOCAL=preservar\n")
    (destino / "meu-arquivo.txt").write_text("conteúdo original")
    antes = {p.name: p.read_bytes() for p in destino.iterdir()}
    r = rodar(env)
    assert r.returncode != 0 and "já existe" in r.stderr
    assert {p.name: p.read_bytes() for p in destino.iterdir()} == antes


def test_download_falhou_nao_cria_instalacao_incompleta(instalacao):
    destino, temporarios, env = instalacao
    r = rodar({**env, "TESTE_FALHA_DOWNLOAD": "1"})
    assert r.returncode != 0
    assert not destino.exists()
    assert list(temporarios.iterdir()) == []
