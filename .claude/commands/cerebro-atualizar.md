---
description: Rotina diária do cérebro de YouTube (cron) - varre os canais cadastrados, ingere a legenda dos vídeos novos, destila os novos e mais um lote do acervo, valida e regrava o índice. Ex.: /cerebro-atualizar · /cerebro-atualizar 20
argument-hint: "[quantas notas do acervo destilar além das novas, padrão 10]"
---

Lote do acervo: $ARGUMENTS (vazio = 10)

Siga o **Fluxo B** da skill `cerebro-youtube` do começo ao fim. Você está rodando sem supervisão: não
pergunte nada, não cadastre nem pause canal, não toque em `editorial/`. Feche com o relato curto:
novos por canal, destilados, pendentes, avisos e a saída real do `python3 cerebro.py validar`.
