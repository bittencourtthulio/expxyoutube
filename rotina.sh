#!/usr/bin/env bash
# Rotina do canal, pronta para cron. Uso: ./rotina.sh <rotina> [argumentos]
#
#   manha                   /rotina-da-manha: coleta, diagnóstico, leitura, daily e plano do dia
#   cerebro-atualizar [N]   /cerebro-atualizar: varre e destila o cérebro de YouTube
#   biblioteca-atualizar [N] /biblioteca-atualizar: varre e destila a biblioteca de pautas
#   cerebro-descobrir       /cerebro-descobrir: procura, julga e cadastra canais no cérebro (D-45)
#   biblioteca-descobrir    /biblioteca-descobrir: procura, julga e cadastra canais na biblioteca (D-45)
#   shorts                  agenda os Shorts do dia (python3 shorts.py agendar), direto, sem chamar o Claude
#
# Monta o ambiente que o cron não tem, trava para não rodar duas vezes, grava log em
# planejamento/logs/AAAA-MM-DD_<rotina>.log e chama o Claude Code em modo dontAsk: só as
# ferramentas liberadas abaixo rodam, nada pede confirmação, e segredo nenhum é alcançável.
# Nunca bypassPermissions. CLAUDE_BIN troca o executável (os testes usam um falso).
set -uo pipefail

RAIZ="$(cd "$(dirname "$0")" && pwd)"
ROTINA="${1:-}"
DIRETO=0
case "$ROTINA" in
  shorts) COMANDO="shorts-do-dia"; DIRETO=1 ;;
  manha) COMANDO="rotina-da-manha" ;;
  cerebro-atualizar|biblioteca-atualizar|cerebro-descobrir|biblioteca-descobrir) COMANDO="$ROTINA" ;;
  *) echo "rotina desconhecida: '$ROTINA'. Use manha, shorts, cerebro-atualizar, biblioteca-atualizar, cerebro-descobrir ou biblioteca-descobrir." >&2; exit 64 ;;
esac
shift

export PATH="$RAIZ/.venv/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export USER="${USER:-$(id -un)}" LOGNAME="${LOGNAME:-$(id -un)}"   # o login do Claude fica no Keychain, que pede USER
export LANG="pt_BR.UTF-8" LC_ALL="pt_BR.UTF-8" TZ="America/Sao_Paulo"
export CLAUDE_PROJECT_DIR="$RAIZ"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"

LOGS="$RAIZ/planejamento/logs"
mkdir -p "$LOGS"
LOG="$LOGS/$(date +%Y-%m-%d)_${ROTINA}.log"
TRAVA="$RAIZ/planejamento/.rotina-${ROTINA}.lock"

# Trava por rotina: mkdir é atômico. Trava com mais de 120 minutos é de uma execução que morreu.
if [ -d "$TRAVA" ] && [ -n "$(find "$TRAVA" -maxdepth 0 -mmin +120 2>/dev/null)" ]; then
  rmdir "$TRAVA" 2>/dev/null
fi
if ! mkdir "$TRAVA" 2>/dev/null; then
  echo "$(date '+%F %T') /${COMANDO} já está rodando (trava em planejamento/.rotina-${ROTINA}.lock); nada a fazer." >> "$LOG"
  exit 0
fi
trap 'rmdir "$TRAVA" 2>/dev/null' EXIT

ALLOWED="Read Grep Glob Edit Write Agent Bash(python3:*) Bash(.venv/bin/python:*) Bash(ls:*) Bash(git status:*) Bash(git diff:*)"
DISALLOWED="Read(./tokens/**) Edit(./tokens/**) Write(./tokens/**) Read(./client_secret*.json) Read(./.env) Edit(./.env) Bash(git push:*) Bash(git commit:*)"
PEDIDO="/${COMANDO}${*:+ $*}"

echo "===== início: ${PEDIDO} $(date '+%F %T') =====" >> "$LOG"
if [ "$DIRETO" = 1 ]; then
  # Shorts: script determinístico (fila, slots, cota e journal em shorts.py); não precisa de modelo.
  (cd "$RAIZ" && python3 shorts.py agendar "$@") < /dev/null >> "$LOG" 2>&1
else
  "$CLAUDE_BIN" -p "$PEDIDO" --permission-mode dontAsk --allowedTools "$ALLOWED" --disallowedTools "$DISALLOWED" < /dev/null >> "$LOG" 2>&1
fi
CODIGO=$?
echo "===== fim: ${PEDIDO} (código ${CODIGO}) $(date '+%F %T') =====" >> "$LOG"
exit "$CODIGO"
