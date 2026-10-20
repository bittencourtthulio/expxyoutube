---
name: validar-pautas
description: >
  Rubrica do score de viralização (0 a 100) e o fluxo do `/pautas`: o `validador` cria ângulos novos a
  partir dos vídeos que mais deram certo no canal e das ideias da biblioteca, pontua cada um contra o que
  o público já assiste e registra na fila os que passam de 80. Use também para pontuar um deck do
  `/apresentacao`. Nada aqui renderiza nem publica.
---

# Validar pautas

## Referência (obrigatória)

`python3 apresentacao.py referencia --json`: `top_views` (10 por views crus, com `views_sobre_mediana`,
`pct_assistido`, `taxa_engajamento`, `palavras`) e `top_inscritos` (5 por `inscritos_por_mil_views`, só com
100 views ou mais). Sem diagnóstico, pare e peça o `/analisar-canal`. Hipóteses de formato:
`python3 cerebro.py buscar --tema ideias --praticas` (e `titulo`, `gancho`).

## Rubrica (4 x 25)

| Eixo | O que pesa | Como citar |
|---|---|---|
| Afinidade | tema e palavras batem com os títulos do top_views | "parecido com <título> (N views, X vezes a mediana)" |
| Gancho | promessa clara, ferramenta nomeada, ganho ou conflito concreto | o título proposto e o que ele promete |
| Tração | inscritos_por_mil_views e pct_assistido dos vizinhos no top_inscritos | "vizinho converte N inscritos por mil, M% assistido" |
| Atualidade | fonte recente (nota da biblioteca com data) ou novidade da ferramenta | data da nota ou da novidade |

Score = soma dos quatro. O motivo cita os números da referência eixo a eixo; sem número, não vale. Corte
em 80: abaixo disso é descartar, com o ângulo alternativo no motivo. Não infle score para passar.

## Fluxo do `/pautas`

1. `python3 apresentacao.py candidatas --json`: fila atual, ideias destiladas da biblioteca
   (`planejar.pautas`) e os top vídeos do canal, cada um com `pauta_id`. Pauta que já tem deck não aparece.
2. Crie de 3 a 6 ângulos: variação de um top vídeo (outro recorte, continuação, comparação com outra
   ferramenta, "o que mudou desde"), ou ideia da biblioteca com o ângulo do canal.
3. Pontue cada um pela rubrica e registre só os que passam de 80:
   `python3 apresentacao.py pauta --titulo "..." --angulo "..." --origem "top:<id> | biblioteca/videos/<canal>/<nota>.md | tema" --score N --motivo "..."`.
   A mesma pauta (título e origem) substitui a anterior na fila.
4. Feche com `python3 apresentacao.py lista --json` e o relato: ângulos criados, score e eixos de cada um,
   quais entraram na fila e quais ficaram fora e por quê.

## Pontuar um deck (dentro do `/apresentacao`)

`python3 apresentacao.py validar <slug> --score N --motivo "<eixo a eixo>"`. 80 ou mais abre; abaixo
descarta e só um novo `validar` acima do corte reabre, depois do `apresentador` refazer o ângulo (uma vez).
