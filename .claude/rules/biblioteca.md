# Biblioteca (`biblioteca.py`, `biblioteca/`)

- A biblioteca guarda **sobre o que gravar**: ideias de vídeo destiladas dos canais do território
  (IA e programação para software house). Mesmo motor do cérebro, base separada, taxonomia separada
  (`biblioteca/temas.json`).
- Ideia é ponto de partida, nunca roteiro. Fato, número, preço ou benchmark de vídeo de terceiro só
  entra no roteiro conferido na fonte primária.
- Formato da ideia: `- **Título.** O ângulo. Cabe em: video-longo | short | playlist:<nome>. [tema] [mm:ss]`.
- **Cadastro de canal é automático (D-45, que substitui D-41).** `python3 biblioteca.py descobrir` lista
  candidatos; o `/biblioteca-descobrir` (ou `/biblioteca-canal` sem URL) julga pelos títulos, grava o
  veredito e cadastra os aprovados até `max_canais_por_rodada`, sem perguntar. Todo cadastro entra em
  `python3 decisoes.py registrar --tipo biblioteca`. Pausar ou remover canal continua sendo pedido do Usuário.
- Só o `bibliotecario` escreve nas notas. Correção de motor se faz no `cerebro.py` e pede as duas
  suítes (`tests/test_cerebro.py` e `tests/test_biblioteca.py`).
- Não importe biblioteca e cérebro ao mesmo tempo: o bloqueio do YouTube soma.
- Consumidores: o `planejador` (pautas do plano, via `planejar.py`) e o `roteirista`.
