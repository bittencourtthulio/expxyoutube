# expxyoutube

Sistema genérico para operar seu canal do YouTube. As configurações desta distribuição são exemplos; personalize a voz editorial, os canais e os diretórios locais.

## Equipe

Agentes em `.claude/agents/`: planejador, analista, roteirista, curador, bibliotecario, reviewer, apresentador e validador. Hooks limitam leitura de segredos e escrita por escopo.

## Operação

Use os scripts para obter métricas, pendências, decisões, pautas e referências. Não invente números. Falta de dado não é zero. O painel usa estado local, não incluído no repositório.

Credenciais OAuth, tokens, `.env`, históricos, relatórios, decks e mídias são privados. Não leia nem versione esses arquivos. A distribuição não herda autorizações de outra instalação: obtenha autorização do operador antes de ativar publicação ou cron. O canal de destino deve ser configurado e conferido.

Depois de configurar e autorizar o bot local: link enviado ao bot do YouTube + Aprovar ou prazo = autorização de publicar no principal.

Apresentações usam `python3 apresentacao.py`; não invoque renderizadores diretamente pelos agentes. Testes: `.venv/bin/python -m pytest -q`.
