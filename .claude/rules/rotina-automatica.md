# Rotina automática (`rotina.sh`)

- Rotina `shorts`: roda `python3 shorts.py agendar` direto, sem o Claude, e publica os Shorts do dia por autorização
  permanente (`.claude/rules/shorts.md`). É a única rotina que sobe vídeo.
- Rotinas: `manha` (coleta, diagnóstico, leitura do analista e plano do dia pelo `/rotina-da-manha`),
  `cerebro-atualizar`, `biblioteca-atualizar`, `cerebro-descobrir` e `biblioteca-descobrir`. Cada uma roda
  `claude -p "/<rotina>" --permission-mode dontAsk --allowedTools <lista>`, com trava, log na pasta
  planejamento/logs e o ambiente que o cron não tem.
- O agendamento não é instalado pelo harness (D-27): as linhas de cron sugeridas estão no README.md da raiz,
  e o Usuário decide quando ligar. Rodar à mão: `./rotina.sh manha`.
- A rotina decide dentro dos limites e registra: toda mudança em plano ou harness vai para
  `python3 decisoes.py registrar`. Ela nunca pergunta; o que dependeria do Usuário vira resposta num fio
  da daily com `--aguarda-resposta`.
- Cérebro e biblioteca não importam ao mesmo tempo (o bloqueio do YouTube soma): no cron, horários
  diferentes.
- Limites da rotina (exceto a `shorts`): nenhuma publicação, nenhum commit, nenhum `git push`, nenhuma pausa nem remoção de canal
  cadastrado sem pedido do Usuário (cadastrar pela descoberta é permitido: D-45). Coleta que falhou não vira número inventado: o plano sai com a última
  análise válida e diz por quê.
