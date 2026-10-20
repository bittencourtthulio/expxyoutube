#!/usr/bin/env bash
# Instalação para macOS, Linux e Windows via WSL. Não requer Git nem Python prévio.
set -euo pipefail

main() {
  local destino="${EXPXYOUTUBE_DIR:-$HOME/expxyoutube}"
  local temporario uv_bin ferramentas
  case "$(uname -s)" in
    Darwin|Linux) ;;
    *) printf 'Use macOS, Linux ou o terminal Ubuntu do WSL no Windows.\n' >&2; return 1 ;;
  esac
  for ferramenta in curl tar mktemp; do
    if ! command -v "$ferramenta" >/dev/null 2>&1; then
      printf 'Falta %s. Instale essa ferramenta e execute novamente.\n' "$ferramenta" >&2
      return 1
    fi
  done
  case "$destino" in
    /*) ;;
    *) destino="$PWD/$destino" ;;
  esac
  if [ -e "$destino" ] || [ -L "$destino" ]; then
    printf 'A pasta %s já existe. Nenhum arquivo foi alterado.\n' "$destino" >&2
    printf 'Para abrir a instalação existente: bash %q/iniciar.sh\n' "$destino" >&2
    printf 'Para instalar em outra pasta, defina EXPXYOUTUBE_DIR.\n' >&2
    return 1
  fi

  temporario="$(mktemp -d "${TMPDIR:-/tmp}/expxyoutube.XXXXXX")"
  # Só a pasta temporária é apagada. Uma instalação incompleta fica disponível para diagnóstico.
  trap "$(printf 'rm -rf -- %q' "$temporario")" EXIT
  trap 'printf "\nA instalação não terminou. Confira a mensagem acima antes de tentar novamente.\n" >&2' ERR

  printf '\n  expxyoutube · seu canal, uma equipe inteira\n\n'
  printf '[1/4] Baixando o projeto…\n'
  curl --fail --silent --show-error --location --retry 3 --connect-timeout 30 \
    https://codeload.github.com/bittencourtthulio/expxyoutube/tar.gz/refs/heads/main \
    --output "$temporario/projeto.tar.gz"

  printf '[2/4] Preparando o gerenciador de Python…\n'
  if command -v uv >/dev/null 2>&1; then
    uv_bin="$(command -v uv)"
  elif [ -x "$HOME/.local/bin/uv" ]; then
    uv_bin="$HOME/.local/bin/uv"
  else
    ferramentas="$HOME/.local/bin"
    curl --fail --silent --show-error --location --retry 3 --connect-timeout 30 \
      https://astral.sh/uv/install.sh --output "$temporario/uv-install.sh"
    UV_INSTALL_DIR="$ferramentas" UV_NO_MODIFY_PATH=1 sh "$temporario/uv-install.sh" </dev/null
    uv_bin="$ferramentas/uv"
  fi

  printf '[3/4] Instalando Python 3.11 e as dependências…\n'
  mkdir -p -- "$(dirname "$destino")"
  # mkdir sem -p impede sobrescrever uma pasta criada enquanto o download estava em andamento.
  mkdir -- "$destino"
  tar -xzf "$temporario/projeto.tar.gz" --strip-components=1 -C "$destino"
  "$uv_bin" venv --managed-python --python 3.11 "$destino/.venv" </dev/null
  "$uv_bin" pip install --python "$destino/.venv/bin/python" -r "$destino/requirements.txt" </dev/null

  printf '[4/4] Preparando sua configuração local…\n'
  (umask 077; cp "$destino/.env.example" "$destino/.env")
  chmod +x "$destino/iniciar.sh"
  "$destino/.venv/bin/python" -c 'import googleapiclient, google_auth_oauthlib, yt_dlp; print("Dependências verificadas.")'
  printf '\nPronto! Projeto instalado em %s\n\n' "$destino"
  printf 'Abra o painel com:\n  bash %q/iniciar.sh\n\n' "$destino"
  printf 'O painel funciona sem credenciais; as métricas aparecem depois de conectar seu YouTube.\n'
  printf 'Próximos passos: %s/README.md → Conecte seu canal.\n\n' "$destino"
}

# Em um pipe, o Bash só começa a instalação após ler toda a definição acima.
main "$@"
