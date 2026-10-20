---
name: publicar-youtube
description: Enviar e agendar aulas do Usuário no canal YouTube autorizado, com descrição, capítulos, legenda, playlist e configuração de três pares no teste A/B do Studio. Usar para publicação, agendamento ou retomada de um envio; não dispara publicação a partir de aprovação somente das artes.
---

# Publicar e agendar aulas

## Antes de executar

A autorização explícita do usuário na sessão permite executar o envio e o agendamento no escopo pedido;
não pedir um segundo sim. Aprovação de thumbs, planejamento ou melhoria do harness não autoriza um novo
envio. Daily/cron e os agentes editoriais não acionam publicação automaticamente.

Exceção do bot do YouTube (configuração local): link enviado ao bot do YouTube + Aprovar ou prazo = autorização de publicar no principal. Quem executa é o enviador do bot
(`bot_youtube/enviador.py`), com plano gerado por `bot_youtube/publicar.py`; ver `.claude/rules/bot-youtube.md`.

- Identificar vídeo/pacote aprovado, alias OAuth, ID do canal, data, hora e fuso. Consultar `channels.list(mine=True)`
  com o alias escolhido e comparar o ID. Nome do projeto/token padrão não prova o destino.
- Horário contraditório exige uma pergunta curta; continuar validações e preparo independentes. Não escolher
  silenciosamente entre 1h e 10h. Registrar data absoluta, zona IANA e horário com offset, convertido a UTC.
- Validar o pacote `thumbs.json` com a skill thumbs-youtube já instalada. Usar os JPGs finais, sem refazer artes
  aprovadas. O primeiro par é o padrão inicial; os outros pertencem ao experimento, não a uploads duplicados.
- Conferir vídeo final 16:9, descrição/CTA inicial Seu Site, capítulos reais começando em 00:00 e SRT correspondente.
  Campos de público/conteúdo sintético devem refletir o vídeo real; não aplicar flags de Jev a toda aula.

## Execução reutilizável

No YouTube Squad, preparar um plano seguindo [plano e comandos](references/plano.md). Usar `publicacao.py`
para validação local, envio e consultas; não copiar o script fixo do Jev nem escrever uma nova cadeia ad hoc.
Segredos são lidos pelo cliente via alias, nunca impressos. A sessão principal executa o plano autorizado.
Deixar conversão de horário, hashes, limites de capítulos/SRT, metadados de vídeo e verificações repetitivas
para o Python. Usar a IA para copy/conceitos e revisão contextual/visual; não reimplementar o executor no chat.

O executor confere hashes e canal, mantém lock e journal, envia inicialmente privado, persiste IDs, sobe
miniatura e SRT, cria ou reutiliza playlist e agenda com `privacyStatus=private` + `publishAt` futuro. Atualizar
somente status e preservar as propriedades graváveis já existentes. Conteúdo novo não exige outro token se
já houver credencial válida do canal certo. Login só se realmente necessário.

Se houver erro/timeout em criação, consultar recursos e journal antes de repetir. Não apagar pending, forjar
sucesso ou reenviar para contornar uma verificação atrasada. Guardar o ID da playlist para as aulas seguintes.
O comando enviar é retomável somente no mesmo plano/arquivos; mudou o plano, reconciliar antes de agir.

## Studio e teste A/B

Após a parte API, seguir [procedimento do Studio](references/studio-ab.md). A API pública usada aqui não configura
os três pares do experimento; `thumbnails.set` só define a miniatura padrão. O fluxo do Studio tem duas gravações:
concluir o diálogo do teste e depois Salvar na página. Recarregar para verificar persistência.

**Configurado** ≠ **salvo** ≠ **rodando**. Na aula Jev 01, as três combinações foram salvas, mas o Studio informou
inelegibilidade enquanto privado. Não antecipar publicação para habilitar A/B e não prometer ativação automática
sem evidência. Se houver impedimento, terminar as outras etapas e relatar precisamente o estado do teste.
Não alterar título/thumbnail padrão depois de iniciar o teste: isso pode interrompê-lo.

## Conferência e entrega

- Fazer consultas novas: canal, ID, privacidade/agendamento, processamento HD/duração, descrição, legenda serving,
  miniatura personalizada e associação à playlist correta. Consultas podem demorar a refletir uma escrita;
  repetir **leituras**, com espera limitada, sem repetir upload/update para curar essa demora.
- O Studio removeu a quebra final da descrição: comparar normalizando somente CRLF e quebra final, mantendo
  CTA, capítulos e texto interno intactos. Não usar equivalência que esconda alteração real.
- Se processamento ainda estiver pendente, registrar e retomar consultas; upload concluído não significa HD pronto.
- Depois do horário agendado, `verificar` espera vídeo público sem alterar nada e aceita qualquer título aprovado
  do experimento. Conferir o teste no Studio: título alternativo visível não prova que A/B está rodando.
- Registrar evidência pós-reload do A/B (três títulos exatos, respectivas imagens, aviso atual), hora da consulta e
  pendências. Não marcar todos os itens como prontos por ter recebido HTTP 200.
- Entregar links do vídeo/playlist, data/hora/fuso e o estado real do A/B. Registrar mudanças e reversão no
  DESFAZER.md da aula. Não apagar arquivos nem cancelar agendamento sem pedido.

Referência concreta, incidentes e limites: [Jev 01](references/exemplo.md).

A instalação pública não herda autorizações de sessões anteriores. Configure seu próprio canal e autorize explicitamente a ativação da automação antes de instalar serviços ou cron.
