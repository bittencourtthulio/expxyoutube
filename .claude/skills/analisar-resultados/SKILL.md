---
name: analisar-resultados
description: >
  Coleta as métricas do canal no YouTube, gera o diagnóstico com KPIs e fichas de vídeo e escreve a
  leitura do analista (`leitura.json`). Use para "como foi a semana", "analisa o canal", "por que esse
  vídeo foi bem", pelo `/analisar-canal` e como primeira etapa da `rotina-da-manha`.
---

# Analisar resultados do canal

## Passos

1. **Coleta** (só leitura; o script abre o token pelo apelido do canal):
   `python3 editorial/analises/coletar_youtube.py`. Se sair `erro:`, pare e relate o erro exato:
   - `403 (accessNotConfigured)`: a YouTube Analytics API não está habilitada no projeto do Google Cloud;
   - `credencial expirada ou revogada`: o Usuário refaz o login com `.venv/bin/python auth.py principal`;
   - `quotaExceeded`: a cota do dia acabou (zera à meia-noite do Pacífico).
   Sem coleta nova, a leitura do dia usa a última análise válida e diz isso nos `limites`.
2. **Diagnóstico**: `python3 editorial/analises/diagnostico.py`. Grava
   `editorial/analises/relatorios/<hoje>/diagnostico.json` com `kpis`, `videos` (nota por formato),
   `formatos`, `trafego` e `tendencia`, a partir do retrato mais recente.
3. **Cérebro**: `python3 editorial/analises/consultar_cerebro.py --para analise --saida
   editorial/analises/relatorios/<hoje>/cerebro.json`.
4. **Leitura**: delegue ao agente `analista`, que grava `leitura.json` na mesma pasta com `tese`,
   `subtese`, `kpis`, `achados` (com evidência em arquivo e número), `acoes`, `limites` e `cerebro`
   (`confirma`, `questiona`).
5. **Validação**: `python3 editorial/analises/diagnostico.py validar-leitura` até sair `ok`.

## Como ler (resumo das regras do analista)

- Janela de 7 dias contra os 7 anteriores, terminando no último dia processado (48 a 72 horas de atraso),
  dias no fuso do Pacífico. Panorama de 30 dias ao lado.
- `views` mudou de contagem em 2025 e 2026; `engaged_views` segue a regra antiga.
- Médias vêm agregadas da API. Lacuna nunca vira zero. Short se compara com Short.
- O painel (`.venv/bin/python painel.py`, aba Painel) mostra exatamente esse diagnóstico.
