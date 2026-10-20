# Bot do Telegram do YouTube (`bot_youtube.py`, `bot_youtube/`)

- **O que é.** O Usuário manda no bot do YouTube (bot próprio, separado do @bot_exemplo) o link de um vídeo do
  YouTube. O bot pergunta **Com avatar** ou **Só motion**, a skill `/recriar-aula-youtube` do cursos-ia produz uma
  **aula nova** sobre o mesmo tema (padrão motion, voz do Usuário, três chamadas, CTA Seu Site, legenda, thumb,
  descrição com capítulos) e a prévia chega no Telegram com Aprovar, Ajustar e Cancelar. A aula entra numa **série
  com nome próprio do assunto**; "recriação" nunca aparece em série, título, thumb, descrição, legenda, playlist ou
  tela (configuração local): o bot não sobe o vídeo se aparecer (`publicar.termos_proibidos`). Plano e decisões:
  `docs/integracao-produtor.md` (D-01 a D-34).
- **Autorização (configuração local):** link enviado ao bot do YouTube + Aprovar ou prazo = autorização de publicar no principal.
  Aprovar sobe e agenda na hora, no slot reservado. Sem resposta, o vídeo sobe sozinho **1 h antes do slot**.
  Vídeo esperando ajuste (Ajustar) não sobe. É exceção à regra "publicação só por pedido explícito na sessão
  principal": o pedido explícito é o próprio link mandado ao bot. Nada além disso publica sozinho.
- **Canal:** `principal` = Seu Canal, `UC_EXEMPLO_CONFIGURE_O_SEU` (D-01), conferido por `channels.list(mine)`
  antes de qualquer escrita (o `publicacao.py` recusa outro canal).
- **Horários:** `YT_SLOTS` no arquivo de chaves do squad (ex.: `YT_SLOTS=10:00,16:00,20:00`), os mesmos todo dia,
  fuso America/Sao_Paulo. O slot é o primeiro livre a 90 min ou mais (`YT_ANTECEDENCIA_MIN`), olhando o
  `publishAt` dos vídeos agendados no canal e os pedidos do bot com horário reservado. Slot perdido (bot parado,
  Mac dormindo) ganha outro, com aviso.
- **Token e chat:** `TELEGRAM_YT_BOT_TOKEN` e `TELEGRAM_YT_CHATID` no arquivo de chaves da raiz, que agente nenhum
  lê. O token nunca vai para log, prompt nem para o claude da produção (a produção roda sem nenhuma `TELEGRAM_*`).
- **Produção:** `bot_youtube/producao.py` baixa a referência (yt-dlp), transcreve (whisper local), tira quadros e
  roda `claude -p "/recriar-aula-youtube <pasta> <pedido> <modo>"` com cwd no `<CURSOS_IA_DIR>`, sem poder ler chaves
  nem tokens nem rodar o `publicacao.py`, até `YT_TEMPO_PRODUCAO_MIN` (240). Um pedido por vez. Precisa de 8 GB
  livres (`YT_DISCO_MIN_GB`). Modo avatar usa o MCP heygen do escopo do projeto cursos-ia (OAuth, sem chave); se a
  sonda da subida (`estado/bot-youtube/sonda-heygen.json`) não deu `ok`, o pedido sai só motion, com aviso.
- **Envio:** só o enviador do bot (`bot_youtube/enviador.py` → `publicar.py` → `publicacao.py validar` e `enviar` com
  journal por pedido em `estado/bot-youtube/pedidos/<pedido>/publicacao-estado.json`). Antes, o bot registra a
  revisão `entrega` da aula. Journal com passo pendente: `falhou` pedindo reconciliação, nunca repetição.
  Login expirado: `bloqueado` com o comando `.venv/bin/python auth.py principal`.
- **Cancelar depois do upload:** o vídeo fica privado, sem agendamento (`videos.update` sem `publishAt`, campos de
  status preservados), e o slot volta a ficar livre. Nada é apagado (D-18). Pela CLI: `bot_youtube.py desagendar <id>`.
- **Estado:** `estado/bot-youtube/pedidos.jsonl` (eventos, só acréscimo), `telegram.json` (offset e avisos),
  `bot.log`. Pergunta sobre pedido: `python3 bot_youtube.py fila|ver <pedido>`.
- **Serviço:** LaunchAgent `com.canal.telegram-bot-youtube` (`python3 bot_youtube.py instalar|desinstalar`), uma
  instância só (`estado/bot-youtube/bot.lock`). `python3 bot_youtube.py verificar` confere bot, chat, slots e canal.
- **Verificador:** `.venv/bin/python -m pytest tests/test_bot_*.py`.

A instalação pública não herda autorizações de sessões anteriores. Configure seu próprio canal e autorize explicitamente a ativação da automação antes de instalar serviços ou cron.
