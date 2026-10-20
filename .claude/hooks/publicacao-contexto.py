"""Roteamento de publicação; não publica, não aprova e não altera a solicitação."""
import json
import re
import sys
from pathlib import Path


def context(event):
    prompt = event.get('prompt', '') if isinstance(event, dict) else ''
    if not isinstance(prompt, str):
        return None
    video = re.search(r'\b(youtube|studio|aulas?|vídeos?|videos?|canais|canal)\b', prompt, re.I)
    action = re.search(r'\b(agend\w*|public\w*|upload|envi\w*|subir|postar)\b', prompt, re.I)
    experiment = re.search(r'\bteste\s+a\s*/?\s*b\b', prompt, re.I)
    if not ((video and action) or experiment):
        return None
    skill = Path(__file__).resolve().parents[1] / 'skills/publicar-youtube/SKILL.md'
    return {'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext':
        f'Para publicação/agendamento/teste A/B, leia {skill}. Conferir alias e ID do canal, '
        'data/hora/fuso explícitos, pacote aprovado e autorização existente. Usar publicacao.py '
        'com journal; resultado incerto exige reconciliação, não outro upload. Preservar status '
        'gravável; verificar por leituras limitadas. A/B exige Salvar e reload no Studio; salvo '
        'enquanto privado não significa rodando. Pedido de melhorar o harness não autoriza novo envio.'}}


if __name__ == '__main__':
    try:
        result = context(json.load(sys.stdin))
        if result:
            print(json.dumps(result, ensure_ascii=False))
    except (ValueError, TypeError):
        pass
