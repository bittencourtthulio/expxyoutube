# Daily (`daily.py`, `painel.py`, `chat.py`)

- A daily é o canal do Usuário com a equipe. Ele escreve pelo painel (aba Tarefas) ou por
  `python3 daily.py novo`; a equipe responde no mesmo fio com `python3 daily.py responder`. O log é
  só acréscimo: ninguém edita nem apaga linha. Pergunta sobre a daily se responde com
  `python3 daily.py pendentes|regras|lista|ver`.
- Quatro tipos: `tarefa`, `pergunta`, `nao-fazer` (proibição) e `aprendizado` (orientação).
  **Proibição e aprendizado valem desde o momento em que ele escreve**: `python3 daily.py regras` é
  leitura obrigatória antes de planejar, escrever título ou roteiro e revisar.
- **O que o Usuário põe na daily vence decisão da equipe, teste e cérebro.** Só não vence o inviolável
  de `.claude/rules/seguranca.md` (segredos, publicar no canal, `git push`, apagar dado). Pedido que bate
  nisso ganha `recusada` com o porquê.
- **Estruturar, não só lembrar.** Proibição ou orientação vira entrada em `editorial/*.md` com a origem
  "Usuário, daily dNNN", e a resposta diz onde (`--onde`). Toda ação por causa da daily também entra em
  `python3 decisoes.py registrar --daily dNNN`.
- Status: a equipe só usa `fazendo`, `feita`, `recusada`, `respondida` e `aplicada`. Criar, cancelar,
  revogar e finalizar é só do Usuário: nenhum agente roda `daily.py novo|revogar|cancelar|finalizar` nem
  `--autor usuario` (os hooks de `.claude/hooks/regras_agentes.py` barram).
- O chat da reunião (`chat.py`) conversa e pode executar pedido na hora, com as ferramentas liberadas em
  `chat.ALLOWED`. Conversa não vira fio da daily sozinha: se valer para amanhã, registre a decisão.
- A resposta ao vivo de um fio chama o Claude só com `Read,Grep,Glob` e nunca muda status de tarefa.
