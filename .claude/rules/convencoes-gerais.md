# Convenções gerais

- **Fontes de verdade, sem duplicar:** métricas em `editorial/analises/relatorios/` (gerado pelos
  scripts), pedidos do Usuário em `estado/daily.jsonl` (por `daily.py`), decisões em
  `estado/decisoes.jsonl` (por `decisoes.py`), plano em `planejamento/` (por `planejar.py`), referência
  externa em `cerebro/` e `biblioteca/`. Pergunta sobre qualquer um se responde pelo script, nunca
  listando pasta nem lendo o arquivo na mão.
- **Python 3.11 da `.venv`.** Dependências em `requirements.txt`, instaladas com
  `uv pip install --python .venv/bin/python -r requirements.txt`. Nos comandos das rules e skills,
  `python3 X.py` vale o mesmo que `.venv/bin/python X.py`.
- **Verificador único:** `.venv/bin/python -m pytest -q` a partir da raiz. Mudança sem teste que falharia
  com a implementação errada não está pronta. A guarda de rede de `tests/conftest.py` impede teste de
  falar com a API real.
- **Número nunca é estimado.** Métrica ausente é `None` (lacuna), nunca zero. Médias não se somam.
- **Dias da API são do fuso do Pacífico**; a pasta do relatório e o plano usam a data de São Paulo.
- **Texto que sai da equipe:** português do Brasil, "você", frases curtas, sem travessão, sem emoji.
- Arquivos gerados (`cerebro/INDEX.md`, `biblioteca/INDEX.md`, `diagnostico.json`) não se editam à mão.
