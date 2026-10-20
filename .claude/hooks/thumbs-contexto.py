"""UserPromptSubmit: lembra o fluxo somente em pedidos pertinentes; não autoriza nem gera nada."""
import json
import re
import sys
from pathlib import Path


def context(event):
    prompt = event.get('prompt', '') if isinstance(event, dict) else ''
    if not isinstance(prompt, str) or not re.search(r'\b(?:thumb(?:s|nails?)?|miniaturas?)\b|\bcapas?\b.{0,40}\b(?:youtube|vídeos?|videos?)\b', prompt, re.I):
        return None
    skill = Path(__file__).resolve().parents[1] / 'skills/thumbs-youtube/SKILL.md'
    return {'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext':
        f'Para esta tarefa de thumbnails, leia {skill}. Padrão do Usuário: três pares título/thumb; '
        'nome da ferramenta nos dois, logo oficial e paleta da ferramenta; referência facial real; '
        'texto com espaço próprio; abrir JPGs finais e prévia de feed. Validar manifesto e revisão '
        'da versão atual antes da entrega. Respeitar quantidade, escopo e autorizações do pedido; '
        'esta lembrança não inicia geração paga nem publicação.'}}


def main():
    try:
        result = context(json.load(sys.stdin))
    except (ValueError, TypeError):
        return
    if result:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
