---
name: roteiro-youtube
description: >
  Método do pacote de um vídeo do canal: títulos, miniatura, gancho, roteiro em blocos, capítulos e
  descrição, na voz do Usuário. Use quando o pedido for "escreve o roteiro", "títulos para esse vídeo",
  "descrição com capítulos", ou quando o Usuário escolher uma pauta do plano. Quem escreve é o agente
  `roteirista`, em `roteiros/`.
---

# Roteiro de vídeo

## Antes

- Leia `editorial/voz.md`, `editorial/aprendizados.md` e `python3 daily.py regras --json`.
- Pauta da biblioteca: `python3 biblioteca.py buscar --texto "<título>" --ideias`. Fato, número, preço e
  benchmark do vídeo de origem só entram conferidos na fonte primária; o que não deu para conferir fica
  marcado `[conferir]`.
- Referência de formato (hipótese, não regra): `python3 editorial/analises/consultar_cerebro.py --para roteiro`.

## O pacote (`roteiros/AAAA-MM-DD-<slug>.md`)

1. **Títulos + miniaturas**: três pares numerados, salvo quantidade explícita diferente. Para
   conceito, identidade, geração e revisão, seguir `.claude/skills/thumbs-youtube/SKILL.md`.
   Cada título cumpre a promessa do vídeo e complementa seu gancho visual.
2. **Briefing e arquivo final**: uma hipótese por par, nome da ferramenta nos dois, logo oficial
   quando disponível, paleta da ferramenta. O roteirista entrega briefing; a sessão principal
   produz/abre os JPGs com ferramenta de imagem. Não confundir essas etapas.
3. **Gancho (0:00 a 0:30)**: palavra por palavra. Promessa, prova de que vale (tela, resultado), o que
   vem. Sem "fala pessoal, tudo bem".
4. **Roteiro**: blocos com tempo estimado, o que aparece na tela e a ponte para o próximo bloco. Um loop
   aberto no começo que só fecha no fim. Demonstração antes de explicação.
5. **Capítulos**: `00:00 Título` a partir do roteiro.
6. **Descrição**: nas aulas, CTA Seu Site na primeira linha (https://example.com, mais de
   conteúdo do seu canal), seguido da promessa, contexto, links e capítulos conferidos no vídeo.
7. **Formato**: `video-longo` (duração alvo) ou `short` (até 60 s, gancho no primeiro segundo, loop).

## Voz

"Você", direto, primeira pessoa do Usuário, sem travessão, sem emoji no título, termo técnico em inglês
quando é o nome da coisa. Publicação é uma etapa separada, executada pela sessão principal sob pedido explícito com a skill publicar-youtube.
