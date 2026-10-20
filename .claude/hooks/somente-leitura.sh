#!/usr/bin/env bash
# PreToolUse do reviewer: nega edição e comando que altera arquivo ou repositório (regras em regras_agentes.py).
exec python3 "$(dirname "$0")/regras_agentes.py" leitura
