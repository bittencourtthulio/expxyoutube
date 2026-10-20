#!/usr/bin/env bash
# PreToolUse Edit|Write de um agente: só grava dentro do escopo dele (regras em regras_agentes.py).
# Uso no frontmatter do agente: escopo.sh <agente>
exec python3 "$(dirname "$0")/regras_agentes.py" escopo "$1"
