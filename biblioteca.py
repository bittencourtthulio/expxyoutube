"""Biblioteca de pautas: canais do YouTube que falam do que a gente fala viram notas com ideias de vídeo.

É o mesmo motor do `cerebro.py` (cadastro, varredura, legenda, estado, validação), rodando sobre outra base:
`biblioteca/` e `estado/biblioteca.json`. O cérebro guarda como crescer no YouTube; a biblioteca guarda
sobre o que gravar. Quem lê a transcrição e escreve resumo, ideias de conteúdo e ressalvas é o agente
`bibliotecario` (skill `biblioteca-conteudo`), que então marca a nota como `destilado`.

  python3 biblioteca.py canal add https://www.youtube.com/@canal --previa     # confere nome e títulos, não grava nada
  python3 biblioteca.py canal add https://www.youtube.com/@canal [--id slug] [--desde 2025-01-01] [--shorts] [--lives]
  python3 biblioteca.py canal pausar <canal>          # e `canal ativar <canal>`; `canal remover <canal>` só para canal sem nota
  python3 biblioteca.py canais                        # canais, o que já entrou, último vídeo de cada um
  python3 biblioteca.py importar <canal> [--limite 50] [--desde 2025-01-01]   # tudo o que o canal já tem
  python3 biblioteca.py importar <canal> --video <id>   # um vídeo só, inclusive um que tinha sido descartado
  python3 biblioteca.py varrer [canal] [--ultimos 30] # rotina diária: só o que é novo, em todos os canais ativos
  python3 biblioteca.py pendentes [--limite 20]       # notas que ainda são `bruto`, mais novas primeiro
  python3 biblioteca.py buscar --tema agentes [--texto "..."] [--canal x] [--desde data] [--ideias]
  python3 biblioteca.py indice                        # regrava biblioteca/INDEX.md
  python3 biblioteca.py validar                       # frontmatter, temas e seções das notas destiladas
  python3 biblioteca.py status

Estado, retomada, bloqueio do YouTube e códigos de saída são os do motor: ver `cerebro/README.md`.
Todo comando aceita --json.
"""
import sys

import cerebro as motor

BASE = {"id": "biblioteca", "nome": "a biblioteca", "onde": "na biblioteca", "titulo": "Biblioteca de pautas",
        "secao_itens": "Ideias de conteúdo", "item": "ideia", "itens": "ideias", "descricao": __doc__}


def main(argv=None):
    motor.usar_base(BASE)
    return motor.main(argv)


if __name__ == "__main__":
    sys.exit(main())
