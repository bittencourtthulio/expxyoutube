---
description: Procura no YouTube canais que ensinam a crescer no YouTube, julga os candidatos pelos títulos e cadastra sozinho os aprovados no cérebro (até o limite da rodada), importa e destila. Sem confirmação humana (D-45). Ex.: /cerebro-descobrir
argument-hint: "[vazio]"
---

Siga o **Fluxo C** da skill `cerebro-youtube` do começo ao fim. Você está rodando sem supervisão: não
pergunte nada, não toque em `biblioteca/` nem em `editorial/`, não faça commit. Rode
`python3 cerebro.py descobrir --json`, julgue os títulos de cada candidato, grave todo veredito com
`python3 cerebro.py descobrir-veredito ...` e cadastre os aprovados com `python3 cerebro.py canal add <url>`
até `max_canais_por_rodada`, importe `importar_por_rodada` vídeos de cada um e destile os mais novos pelo
`curador`. Registre cada cadastro em `python3 decisoes.py registrar --tipo cerebro`. Feche com o relato:
candidatos, vereditos com o número que sustentou cada um, canais cadastrados, importados, destilados e a
saída real do `python3 cerebro.py validar`.
