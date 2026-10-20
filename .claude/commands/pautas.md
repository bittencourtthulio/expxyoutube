---
description: O validador cria ângulos novos a partir dos vídeos que mais deram certo no canal e das ideias da biblioteca, pontua cada um (0 a 100) contra o que o público já assiste e registra na fila os que passam de 80. Ex.: /pautas · /pautas "só sobre agentes"
argument-hint: "[foco opcional]"
---

Foco: $ARGUMENTS (vazio = todo o território)

Delegue ao agente `validador` seguindo a skill `validar-pautas`: `python3 apresentacao.py referencia --json`
como base, `python3 apresentacao.py candidatas --json` como matéria-prima, de 3 a 6 ângulos, score com
os quatro eixos citando números, e `python3 apresentacao.py pauta ...` só para os que passam de 80.
Sem diagnóstico, pare e peça o `/analisar-canal`. Feche com a saída real de
`python3 apresentacao.py lista` e o relato: ângulos, scores, o que entrou e o que ficou fora e por quê.
