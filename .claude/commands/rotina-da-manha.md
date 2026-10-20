---
description: Rotina da manhã do canal (cron ou à mão) - coleta as métricas do YouTube, gera o diagnóstico, escreve a leitura do analista, trata os pendentes da daily e monta o plano do dia. Ex.: /rotina-da-manha
argument-hint: "[vazio]"
---

Siga a skill `rotina-da-manha` do começo ao fim. Você está rodando sem supervisão: não pergunte nada,
não publique nada, não faça commit. O que depender do Usuário vira resposta num fio da daily com
`--aguarda-resposta`. Feche com o relato curto: KPIs da semana (número e arquivo), pendentes tratados,
pautas escolhidas e o que falhou, com a saída real de `python3 editorial/analises/diagnostico.py validar-leitura`.
