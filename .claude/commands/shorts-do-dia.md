---
description: Agenda os Shorts do dia no canal (um por slot de YT_SHORTS_SLOTS), pegando da pasta de reels só o que ainda não foi postado. Ex.: /shorts-do-dia · /shorts-do-dia --simular
argument-hint: "[--simular] [--dia AAAA-MM-DD] [--max N]"
---

Você está rodando sem supervisão. A autorização é permanente e está em `.claude/rules/shorts.md`: este comando
agenda os Shorts do dia, e só isso.

1. Rode `python3 shorts.py status` e cite a fila, o teto e os travados.
2. Rode `python3 shorts.py agendar $ARGUMENTS`. O script escolhe os slots livres de hoje, sobe cada reel
   privado com `publishAt`, respeita a cota e grava o journal em `estado/shorts/eventos.jsonl`.
3. Relate o que saiu: pastas, títulos, horários e video_id de cada Short, os pulados com o motivo e os avisos.

Se a saída trouxer `erro` ou `travados`, pare e relate; nunca rode `agendar` de novo para contornar. Resultado
incerto fica registrado no relato com o comando `python3 shorts.py reconciliar` para o Usuário rodar depois de olhar o Studio; a rotina não o executa. Não edite `.env`, tokens nem
`estado/shorts/`, não faça commit e não publique nada fora deste script.
