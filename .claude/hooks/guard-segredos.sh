#!/usr/bin/env bash
# Hook global (PreToolUse, registrado em .claude/settings.json): nenhuma sessão lê, grava ou cita os
# segredos do canal. Vale para a sessão principal, o chat do painel e a rotina, não só para subagentes.
# Segredos: tokens/ (refresh tokens do OAuth), client_secret*.json (credencial do app) e .env.
# Sai com 2 (bloqueia) e explica no stderr; qualquer outra coisa passa.
exec python3 "$(dirname "$0")/guard_segredos.py"
