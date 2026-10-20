#!/usr/bin/env bash
set -euo pipefail
RAIZ="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -x "$RAIZ/.venv/bin/python" ]; then
  printf 'Instalação incompleta: o ambiente Python não foi encontrado. Consulte o README.\n' >&2
  exit 1
fi
cd -- "$RAIZ"
exec "$RAIZ/.venv/bin/python" "$RAIZ/painel.py" "$@"
