---
description: Gera uma apresentação animada (6 a 10 slides, Remotion, palco com tela cheia) a partir de um tema, URL, texto colado ou vazio (a fila de pautas escolhe), com score do validador antes do render e CTA do Seu Site no fim. Ex.: /apresentacao · /apresentacao Supabase para software house · /apresentacao https://n8n.io/blog/x
argument-hint: "[tema | URL | texto | vazio]"
---

Pauta: $ARGUMENTS (vazio = fluxo D, o `validador` escolhe entre `python3 apresentacao.py candidatas --json`)

Siga a skill `apresentacao` na ordem: deck pelo `apresentador`, `python3 apresentacao.py validar-deck <slug>`,
score pelo `validador` (skill `validar-pautas`, `python3 apresentacao.py validar`), render só com 80 ou mais
(`python3 apresentacao.py render <slug>` com timeout de 600000 ms), conferência dos PNGs e
`python3 apresentacao.py abrir <slug>`. Abaixo de 80: um ângulo alternativo, uma segunda tentativa, e o
relato explica se ficou descartada. Nada é publicado. Feche com o relato da skill e a saída real de
`python3 apresentacao.py lista`.
