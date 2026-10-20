---
description: Procura canais novos do território no YouTube, julga os candidatos pelos títulos e cadastra sozinho os aprovados na biblioteca (até o limite da rodada), importa e destila. Sem confirmação humana (D-45, substitui D-41). Ex.: /biblioteca-descobrir
argument-hint: "[vazio]"
---

Siga o **Fluxo C** da skill `biblioteca-conteudo` do começo ao fim. Você está rodando sem supervisão: não
pergunte nada, não toque em `cerebro/` nem em `editorial/`, não faça commit. Rode
`python3 biblioteca.py descobrir --json`, julgue os títulos de cada candidato, grave todo veredito com
`python3 biblioteca.py descobrir-veredito ...` e cadastre os aprovados com `python3 biblioteca.py canal add <url>`
até `max_canais_por_rodada`, importe `importar_por_rodada` vídeos de cada um e destile os mais novos pelo
`bibliotecario`. Registre cada cadastro em `python3 decisoes.py registrar --tipo biblioteca`. Feche com o
relato: candidatos, vereditos com o número que sustentou cada um, canais cadastrados, importados,
destilados e a saída real do `python3 biblioteca.py validar`.
