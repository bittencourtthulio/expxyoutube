# Shorts do YouTube (`shorts.py`, `estado/shorts/`)

- **O que é.** Os reels prontos da pasta de vídeos do Instagram (`YT_SHORTS_DIR`, padrão
  `midias/shorts`) viram Shorts do canal. Um reel é toda pasta com `<pasta>/<pasta>.mp4` e
  `legenda.txt`. `python3 shorts.py agendar` sobe um por slot livre do dia, privado com `publishAt`.
- **Autorização (configuração local):** o pedido de automatizar os Shorts do dia é a autorização configurada localmente de
  subir e agendar no `principal` pelo `shorts.py`, sem confirmação a cada rodada. É exceção à regra "daily e cron não
  publicam", nos mesmos moldes da do bot do YouTube (`.claude/rules/bot-youtube.md`). Só o `shorts.py` sobe Short;
  nenhum agente editorial roda `agendar`. O canal é conferido por `channels.list(mine)` antes de qualquer escrita.
- **Horários:** `YT_SHORTS_SLOTS` no arquivo de chaves da raiz (HH:MM, fuso America/Sao_Paulo). Só o dia de hoje: o que
  não coube (slot no passado, a menos de `YT_ANTECEDENCIA_MIN`, ocupado no canal ou no journal) fica sem Short.
- **Controle do que já foi postado:** `estado/shorts/eventos.jsonl`, só acréscimo, uma linha por evento e a pasta como
  chave (`enviando`, `agendado` com video_id e sha256, `falhou`, `verificar`, `liberado`, `excluido`). A fila é a fonte
  menos os reels que já têm `agendado`, `falhou` ou `excluido`, e menos título repetido. Pergunta sobre a fila se responde
  com `python3 shorts.py fila|status`.
- **Ajustes** em `estado/shorts/config.json`: `excluir_prefixos` (padrão `[]`; configure os prefixos que quiser ignorar)
  e `max_total` (teto de Shorts agendados; `null` = sem teto). Quem decide é o Usuário.
- **Cota:** cada upload custa 1600 unidades da Data API (padrão 10 mil por dia, `YT_COTA_DIA`); cabem 6 por dia com
  folga pequena. O script corta o lote pela cota do dia e para em `quotaExceeded` sem marcar o reel como usado.
- **Resultado incerto** (upload que caiu no meio, agendamento não confirmado) trava a fila: nada novo sobe até
  `python3 shorts.py reconciliar <pasta> --video-id ID` ou `--nao-subiu`, depois de conferir no Studio. Nunca repetir
  upload às cegas. `liberar` devolve à fila um reel `falhou`; `excluir` tira um reel da fila.
- **Texto público:** título do tema da legenda (até 100 caracteres), descrição sem a chamada "Comenta X" do Instagram,
  com o CTA do Seu Site e `#Shorts`. "Recriação" nunca aparece (o reel é pulado). O vídeo precisa ser vertical, de até
  180 s e com áudio. Sem thumbnail, legenda SRT nem playlist.
- **Rotina:** `./rotina.sh shorts` roda o script direto (sem chamar o Claude), com trava e log em
  `planejamento/logs/`; `/shorts-do-dia` faz o mesmo pela sessão. O agendamento não é instalado pelo harness: linha
  de cron no README.md.
- **Verificador:** `.venv/bin/python -m pytest -q tests/test_shorts.py`.

A instalação pública não herda autorizações de sessões anteriores. Configure seu próprio canal e autorize explicitamente a ativação da automação antes de instalar serviços ou cron.
