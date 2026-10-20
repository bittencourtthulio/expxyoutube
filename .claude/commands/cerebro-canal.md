---
description: Cadastra um canal do YouTube no cérebro (como crescer no YouTube), importa o acervo e destila os mais novos, sem confirmação humana (D-45). Sem URL, procura o canal sozinho pelo /cerebro-descobrir. Ex.: /cerebro-canal https://www.youtube.com/@PaddyGalloway desde 2025-06-01 · /cerebro-canal
argument-hint: "[url do canal] [desde AAAA-MM-DD] [com shorts] [destilar N]"
---

Pedido (pode estar vazio): $ARGUMENTS

**Sem URL:** siga o **Fluxo C** da skill `cerebro-youtube`, igual ao `/cerebro-descobrir`: busque canais
candidatos, julgue pelos títulos, grave os vereditos e cadastre os aprovados até `max_canais_por_rodada`.

**Com URL:** siga o **Fluxo A** da skill `cerebro-youtube`. Comece com `python3 cerebro.py canal add <url> --previa`
e confira você mesmo, pelos últimos títulos, se o canal fala de crescer no YouTube. Se a maior parte dos
títulos for do tema, cadastre sem perguntar; se não for, não cadastre e relate os títulos. Canal com mais
de 300 vídeos e sem "desde": use o corte de 12 meses e diga quantos vídeos ficaram de fora.

Você está rodando sem supervisão: não pergunte nada, não faça commit. Registre o cadastro em
`python3 decisoes.py registrar --tipo cerebro`.
