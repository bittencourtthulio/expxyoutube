---
description: Cadastra um canal do território na biblioteca de pautas, importa o acervo e destila os mais novos em ideias de vídeo, sem confirmação humana (D-45). Sem URL, procura o canal sozinho pelo /biblioteca-descobrir. Ex.: /biblioteca-canal https://www.youtube.com/@canal desde 2025-09-01 · /biblioteca-canal
argument-hint: "[url do canal] [desde AAAA-MM-DD] [com shorts] [destilar N]"
---

Pedido (pode estar vazio): $ARGUMENTS

**Sem URL:** siga o **Fluxo C** da skill `biblioteca-conteudo`, igual ao `/biblioteca-descobrir`.

**Com URL:** siga o **Fluxo A** da skill `biblioteca-conteudo`. Comece com
`python3 biblioteca.py canal add <url> --previa` e confira você mesmo, pelos últimos títulos, se o canal
fala de IA aplicada a software, SaaS ou software house. Se a maior parte dos títulos for do tema, cadastre
sem perguntar; se não for, não cadastre e relate os títulos. Assunto de IA envelhece rápido: sem "desde",
use o corte de 12 meses.

Você está rodando sem supervisão: não pergunte nada, não faça commit. Registre o cadastro em
`python3 decisoes.py registrar --tipo biblioteca`.
