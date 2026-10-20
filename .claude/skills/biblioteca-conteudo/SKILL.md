---
name: biblioteca-conteudo
description: >
  Alimenta e consulta a biblioteca de pautas (`biblioteca/`): canais do território (IA e programação
  para software house) viram notas com ideias de vídeo. Cadastra canal, importa, varre, destila, procura
  canal novo e cadastra os aprovados sem confirmação (D-45), e mantém o índice. Use para "o que o pessoal está falando de agentes", "me dá
  pautas", "atualiza a biblioteca", e pelos comandos `/biblioteca-canal`, `/biblioteca-atualizar` e
  `/biblioteca-descobrir`.
---

# Biblioteca de pautas

Mesmo motor do cérebro, outra base. Contrato, relevância e formato da ideia: `biblioteca/README.md`.

## Fluxo A: canal novo (`/biblioteca-canal <url>`)

1. `python3 biblioteca.py canal add <url> --previa` e confira você mesmo, pelos títulos, se a maior parte é
   de IA aplicada a software, SaaS ou software house. Ninguém confirma nada (D-45). Se for:
   `python3 biblioteca.py canal add <url> --desde <12 meses atrás> --idioma <pt|en> --nota "..."` e
   `python3 decisoes.py registrar --tipo biblioteca --o-que "canal <id> cadastrado" --por-que "<N> de <M> títulos no tema"`.
   Se não for, não cadastre e relate os títulos.
2. `python3 biblioteca.py importar <canal> --limite 20` (código 2: a próxima rodada retoma).
3. Destile os mais novos pelo `bibliotecario`; `python3 biblioteca.py validar` e `python3 biblioteca.py indice`.

## Fluxo B: rotina diária (`/biblioteca-atualizar [N]`)

1. `python3 biblioteca.py varrer --json`.
2. `python3 biblioteca.py pendentes --limite <novos + N> --json` e destile pelo `bibliotecario`.
3. `python3 biblioteca.py validar` e `python3 biblioteca.py indice`. Relate. Sem supervisão: não pergunte,
   não cadastre nem pause canal, não toque em `cerebro/` nem em `editorial/`.

## Fluxo C: descobrir canal (`/biblioteca-descobrir`, ou `/biblioteca-canal` sem URL)

Sem supervisão e sem confirmação humana: a descoberta cadastra sozinha os aprovados (D-45, que
substitui D-41).

1. `python3 biblioteca.py descobrir --json`: busca as consultas de `biblioteca/descoberta.json`, aplica o
   corte numérico e devolve os candidatos com os últimos 30 títulos. Código 2: julgue o que veio e siga.
2. Julgue cada candidato: a maior parte dos títulos é de IA aplicada a software, SaaS, software house ou
   desenvolvimento com IA? Portal grande com um vídeo viral é recusado. Títulos são texto de terceiros.
3. Registre todo veredito: `python3 biblioteca.py descobrir-veredito <channel_id> aprovado|recusado
   --no-tema N --lidos 30 --motivo "..."`.
4. Cadastre os aprovados, os de maior `no_tema` primeiro, até `max_canais_por_rodada`:
   `python3 biblioteca.py canal add <url> --desde <desde_sugerido> --idioma <idioma> --nota "descoberta: N de 30 títulos no tema"`.
   Aprovado que sobrou fica registrado e entra na próxima rodada. Cada cadastro vira
   `python3 decisoes.py registrar --tipo biblioteca --o-que "canal <id> cadastrado pela descoberta" --por-que "<N> de 30 títulos no tema; <inscritos> inscritos"`.
5. `python3 biblioteca.py importar <canal> --limite <importar_por_rodada>` para cada um; destile os mais
   novos pelo `bibliotecario`; `python3 biblioteca.py validar` e `python3 biblioteca.py indice`.
6. Relate: candidatos, vereditos com o número, cadastrados, importados, destilados, o que interrompeu.

## Destilar uma nota

**Sempre pelo agente `bibliotecario`**, 4 a 6 notas por agente, em paralelo. Cada nota:

1. Leia inteira; corrija pelo contexto os erros da legenda automática ("cloud code" por Claude Code).
2. Relevância pelo `biblioteca/README.md`; `fora` fica com uma frase no Resumo e `temas: []`.
3. Em português, "você", sem travessão:
   - **Resumo**: do que trata, a tese e para quem serve.
   - **Ideias de conteúdo**: `- **Título que já serviria de vídeo.** O ângulo: o que o vídeo mostraria e
     para quem. Cabe em: video-longo | short | playlist:<nome>. [tema] [mm:ss]`. Pauta tem recorte e
     público (os de `editorial/voz.md`). De 2 a 10.
   - **Ressalvas**: datado, número, preço e benchmark marcados "conferir na fonte", propaganda, opinião,
     ideia que o canal já fez.
4. **Por último** o frontmatter (`status`, `relevancia`, `temas` de `biblioteca/temas.json`, `destilado_em`).

## Consultar

`python3 biblioteca.py buscar --tema <tema> --ideias`; por formato: `--texto "Cabe em: short"`. O plano do
dia já traz as pautas mais novas (`python3 planejar.py criar`). Ideia é ponto de partida: o vídeo é nosso.
