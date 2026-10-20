---
description: Revisão só leitura das mudanças do repositório pelo agente reviewer (correção, segurança, testes, rules). Ex.: /review · /review painel.py
argument-hint: "[arquivo ou área opcional]"
---

Foco: $ARGUMENTS (vazio = todo o `git diff`)

Despache só o agente `reviewer` sobre as mudanças (ele roda `git diff`, `git status` e
`.venv/bin/python -m pytest -q`). Devolva o relatório dele como veio: BLOQUEANTE, IMPORTANTE, SUGESTÃO,
cada item com arquivo:linha. Não corrija nada nesta rodada.
