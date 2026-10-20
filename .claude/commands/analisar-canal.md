---
description: Analisa o desempenho do canal no YouTube - coleta, diagnóstico e leitura do analista (leitura.json), sem montar o plano. Ex.: /analisar-canal · /analisar-canal "por que os Shorts caíram?"
argument-hint: "[pergunta opcional para guiar a leitura]"
---

Pergunta do Usuário (pode estar vazia): $ARGUMENTS

Siga a skill `analisar-resultados`. Delegue a leitura ao agente `analista`. Se houver pergunta, a
leitura responde a ela primeiro, com número e arquivo. Nunca estime número: métrica ausente é lacuna.
Feche com a tese da semana e a saída real de `python3 editorial/analises/diagnostico.py validar-leitura`.
