#!/usr/bin/env bash
# PreToolUse Bash de um agente: só um comando simples da lista dele (regras em regras_agentes.py).
# Uso no frontmatter do agente: bash-permitido.sh <agente>
exec python3 "$(dirname "$0")/regras_agentes.py" bash "$1"
