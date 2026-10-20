---
name: rotina-da-manha
description: >
  Rotina diária do canal, sem supervisão: análise do YouTube, tratamento dos pendentes da daily e plano
  do dia com pautas da biblioteca. Use pelo `/rotina-da-manha` (cron, via rotina.sh manha) ou quando o
  Usuário pedir "roda a rotina". Nunca publica, nunca faz commit, nunca pergunta.
---

# Rotina da manhã

Você é o `planejador` conduzindo a manhã. Nada depende do Usuário agora: o que dependeria vira resposta
num fio da daily com `--aguarda-resposta`.

## 0. Daily primeiro

1. `python3 daily.py revisar --json`, `python3 daily.py pendentes --json` e `python3 daily.py regras --json`.
2. Para cada pendente, pelo tipo:
   - `tarefa`: `python3 daily.py responder <id> --autor planejador --status fazendo --texto "..."`, execute,
     e feche com `--status feita --onde "<arquivo ou comando>"` ou `--status recusada` com o porquê (bate
     em `.claude/rules/seguranca.md`);
   - `nao-fazer` e `aprendizado`: vire estrutura em `editorial/*.md` com a origem "Usuário, daily dNNN" e
     feche com `--status aplicada --onde editorial/<arquivo>.md`;
   - `pergunta` de análise: delegue ao `analista`; as suas você responde com `--status respondida`.
3. Toda ação vinda da daily: `python3 decisoes.py registrar --daily <id> ...`.

## 1. Análise

Siga a skill `analisar-resultados` (coleta, diagnóstico, cérebro, leitura do `analista`, validação).
Coleta que falhou: siga com a última análise válida e registre o motivo nos `limites` e no relato.

## 2. Plano do dia

1. `python3 planejar.py criar --json` (ou `--refazer` se a análise de hoje saiu depois de um plano já criado).
2. Leia as pautas contra `editorial/voz.md`, `editorial/cadencia.md` e as regras em vigor; cruze com
   `python3 editorial/analises/consultar_cerebro.py --para plano`.
3. Escolha até três pautas para a semana e registre o porquê com `python3 planejar.py nota --texto "..."`.
   Se uma pauta pede roteiro, deixe no plano a indicação para o `roteirista`; roteiro não se escreve sem
   o Usuário escolher a pauta.

## 3. Fechar

- `python3 daily.py pendentes` volta vazio, ou só com o que está `fazendo` e explicado.
- `.venv/bin/python -m pytest -q` verde se você mudou algum arquivo do harness.
- Relato curto: KPIs com número e arquivo, pendentes tratados, pautas escolhidas, o que falhou.

Nunca: publicar, subir vídeo, moderar comentário, `git commit`, `git push`, ler segredo, pausar ou remover
canal cadastrado sem pedido do Usuário.
