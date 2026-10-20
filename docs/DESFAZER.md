# Desativar o bot local

Use `python3 bot_youtube.py desinstalar` para remover o serviço instalado por este projeto.

Se for necessário fazê-lo manualmente, substitua `<uid>` pelo seu identificador de usuário:

```sh
launchctl bootout gui/<uid>/com.canal.telegram-bot-youtube
rm ~/Library/LaunchAgents/com.canal.telegram-bot-youtube.plist
```

Para retirar um agendamento criado pelo bot: `python3 bot_youtube.py desagendar <video_id>`. Confira antes o canal e o vídeo de destino.
