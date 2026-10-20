# Apresentações (`apresentacao.py`, `apresentacoes/`)

- Uma apresentação é um deck de 6 a 10 slides animados (Remotion, 1920x1080, um MP4 por slide) para o
  Usuário apresentar ao vivo, sem roteiro falado. Vive em `apresentacoes/decks/<slug>/`: `deck.json` (só o
  `apresentador` escreve), `estado.json` e `fila.json` (só pelo script), a pasta de ativos e a de saída (render).
  Schema do deck: topo de `tests/decks.py`; projeto Remotion em `apresentacoes/motion/`.
- **Score antes do render.** O `validador` pontua com `python3 apresentacao.py validar` pela rubrica de
  quatro eixos (afinidade, gancho, tração, atualidade) sobre `python3 apresentacao.py referencia`, o que o
  público já assiste. O motivo cita números; abaixo de 80 o deck fica descartado e não renderiza. Deck
  descartado só reabre com um novo `validar` acima do corte, depois de um ângulo novo (uma tentativa).
- **Estados:** `aberta` e `gravada` alternam pelo painel (aba Apresentações) ou por
  `python3 apresentacao.py status`; `descartada` não reabre por status. A galeria ordena por score: a
  primeira em aberto é a pauta mais quente para gravar.
- O último slide é sempre o CTA do Seu Site (`example.com`) com o screenshot do site
  (`python3 apresentacao.py screenshot`). A identidade é a da ferramenta do tema (cor e ícone via
  `python3 apresentacao.py marca`, tabela curada em `apresentacoes/comuns/marcas.json`) ou a CANAL.
- Slide é conteúdo da aula. Métrica do nosso canal (views, inscritos, diagnóstico) nunca entra em slide;
  número em slide é do tema, com fonte externa; sem travessão nem meia-risca; `validar-deck` recusa.
- Render (`python3 apresentacao.py render <slug>`) leva minutos: Bash com timeout de 600000 ms. Nenhum
  agente roda `node`, `npx` ou `npm` direto. Remotion sem chave de licença: se as pessoas que operam o
  código Remotion na CANAL somarem 4 ou mais, é preciso a Company License; o Usuário confirma o headcount.
- Nada aqui publica, sobe vídeo ou toca o canal. A fila (`/pautas`) só sugere; gravar é decisão do Usuário.
