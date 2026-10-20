# expxyoutube

Sistema em Python para operar um canal do YouTube com agentes do Claude Code: métricas, painel web, daily, planejamento editorial, biblioteca de referências, apresentações e fluxos opcionais de publicação.

Esta distribuição começa sem credenciais, métricas, histórico, canais cadastrados ou identidade empresarial. Personalize `editorial/voz.md`, `editorial/cadencia.md` e as configurações antes de usar.

## Instalação

Requer Python 3.11 ou superior e um sistema Unix. Claude Code é necessário para as rotinas de agentes. As apresentações usam Node.js 20 e Remotion; confira a licença do Remotion para o seu uso.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Crie suas próprias credenciais OAuth de aplicativo para computador no Google Cloud, habilite YouTube Data API v3 e YouTube Analytics API e salve `client_secret.json` na raiz. Autentique localmente:

```bash
.venv/bin/python auth.py principal
.venv/bin/python painel.py
```

O painel abre em http://127.0.0.1:8766. Credenciais e estado permanecem locais.

## Uso

```bash
.venv/bin/python editorial/analises/coletar_youtube.py
.venv/bin/python editorial/analises/diagnostico.py
.venv/bin/python daily.py pendentes
.venv/bin/python planejar.py criar
.venv/bin/python cerebro.py canal add https://www.youtube.com/@canal --previa
.venv/bin/python biblioteca.py buscar --tema agentes --ideias
```

Configure suas fontes em `cerebro/canais.json` e `biblioteca/canais.json`, e adapte temas e consultas de descoberta ao seu público. Os arquivos iniciais não contêm acervo.

## Apresentações

Os comandos `/apresentacao` e `/pautas` preparam e validam decks. O projeto de slides está em `apresentacoes/motion/`; seus decks locais ficam em `apresentacoes/decks/`.

```bash
.venv/bin/python apresentacao.py lista
.venv/bin/python apresentacao.py render <slug>
```

O CTA de exemplo usa `example.com`: substitua-o pelo seu site antes de produzir material final.

## Rotinas opcionais

Nenhum serviço ou agendamento é instalado automaticamente. Para usar o bot, configure TELEGRAM_YT_BOT_TOKEN, TELEGRAM_YT_CHATID, YT_CANAL_ALIAS e YT_CANAL_ID. A integração de produção de vídeo requer uma instalação externa compatível indicada por CURSOS_IA_DIR; ela não está incluída.

Após configurar e autorizar a automação na sua instalação, exemplos de cron (substitua o caminho):

```cron
30 6 * * * /caminho/do/projeto/rotina.sh manha
0 4 * * * /caminho/do/projeto/rotina.sh cerebro-atualizar
0 3 * * * /caminho/do/projeto/rotina.sh biblioteca-atualizar
0 9 * * 1 /caminho/do/projeto/rotina.sh biblioteca-descobrir
0 9 * * 4 /caminho/do/projeto/rotina.sh cerebro-descobrir
```

## Testes

```bash
.venv/bin/python -m pytest -q
```

Os testes bloqueiam conexões externas. O estado, os tokens e os arquivos de produção são ignorados pelo Git. Não adicione arquivos operacionais com `git add -f`.
