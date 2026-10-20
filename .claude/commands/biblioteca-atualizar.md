---
description: Rotina diária da biblioteca de pautas (cron) - varre os canais do território, ingere o que é novo, destila em ideias de vídeo, valida e regrava o índice. Ex.: /biblioteca-atualizar · /biblioteca-atualizar 20
argument-hint: "[quantas notas do acervo destilar além das novas, padrão 10]"
---

Lote do acervo: $ARGUMENTS (vazio = 10)

Siga o **Fluxo B** da skill `biblioteca-conteudo`. Sem supervisão: não pergunte, não cadastre nem pause
canal, não toque em `cerebro/` nem em `editorial/`. Feche com novos por canal, destilados, pendentes,
avisos e a saída real do `python3 biblioteca.py validar`.
