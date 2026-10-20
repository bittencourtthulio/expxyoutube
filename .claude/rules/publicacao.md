# Publicação de aulas por pedido explícito

A sessão principal pode executar envio/agendamento autorizado pelo usuário seguindo
`.claude/skills/publicar-youtube/SKILL.md` e `publicacao.py`. Daily/cron e agentes editoriais não publicam (exceção: `shorts.py`, ver `.claude/rules/shorts.md`)
por conta própria; aprovação de arte não é ordem de upload. Não pedir aprovação redundante para escopo já autorizado.

Exceção do bot do YouTube (configuração local): link enviado ao bot do YouTube + Aprovar ou prazo = autorização de publicar no principal. Só o enviador do bot
(`bot_youtube/enviador.py`) sobe esses vídeos, pelo mesmo `publicacao.py`. Regra completa em `.claude/rules/bot-youtube.md`.

- Alias e ID conferidos; data/hora/fuso sem contradição. Canal padrão do squad não prevalece sobre o pedido.
- Plano+hashes+journal com lock; consulta e reconciliação antes de repetir operações incertas.
- Update de status preserva campos graváveis; leitura atrasada gera nova leitura, não novo vídeo.
- Teste A/B: três pares ligados; concluir diálogo, salvar página, recarregar. Salvo e rodando são estados distintos.
- Evidência final: HD, horário/privacidade, conteúdo editorial, SRT, playlist e aviso atual do Studio.

A instalação pública não herda autorizações de sessões anteriores. Configure seu próprio canal e autorize explicitamente a ativação da automação antes de instalar serviços ou cron.
