"""Regressões do pacote: revisões antigas, pares incompletos e nomes ausentes não passam."""
import copy
import importlib.util
import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.claude/skills/thumbs-youtube/scripts/validar.py'
spec = importlib.util.spec_from_file_location('thumb_validator', SCRIPT)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def package(tmp_path):
    # Cabeçalhos sintéticos: estes testes são estruturais, não inspeção de imagem.
    for i in range(3):
        (tmp_path / f'{i}.png').write_bytes(b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', 1280, 720) + bytes([i]))
    doc = {'version': 1, 'tool': 'Jev', 'brand': {'source': 'https://typesafe.ai', 'colors': ['#E58CA1'], 'logo': None, 'logo_note': 'não localizado'},
           'identity': {'method': 'sem pessoa', 'reference': None}, 'variants': [
               {'id': str(i), 'title': f'Jev: teste {i}', 'headline': f'Jev {i}', 'concept': f'hipótese {i}', 'evidence': 'roteiro, 00:12', 'file': f'{i}.png'} for i in range(3)]}
    for item in doc['variants']:
        item['review'] = dict(fingerprint=v.fingerprint(doc, item, tmp_path), reviewer='teste', notes='Sem rosto; fixture estrutural.',
                              face=True, text=True, brand=True, composition=True, feed=True)
    return doc


def test_pacote_e_cli_somente_leitura(tmp_path):
    doc = package(tmp_path)
    path = tmp_path / 'thumbs.json'
    path.write_text(json.dumps(doc))
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    run = subprocess.run([sys.executable, str(SCRIPT), 'validar', str(path)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


@pytest.mark.parametrize('change', ['image', 'title', 'brand', 'headline'])
def test_alteracao_invalida_revisao(tmp_path, change):
    doc = package(tmp_path)
    if change == 'image':
        with (tmp_path / '0.png').open('ab') as f:
            f.write(b'alterada')
    elif change == 'brand':
        doc['brand']['colors'] = ['#FFFFFF']
    else:
        doc['variants'][0][change] += ' mudou'
    assert any('desatualizada' in e for e in v.validate(doc, tmp_path))


@pytest.mark.parametrize('fault', ['missing_tool', 'missing_pair', 'duplicate', 'unreviewed', 'missing_file', 'size'])
def test_erros_concretos(tmp_path, fault):
    doc = package(tmp_path)
    if fault == 'missing_tool':
        doc['variants'][0]['title'] = 'uma IA'
    elif fault == 'missing_pair':
        doc['variants'].pop()
    elif fault == 'duplicate':
        doc['variants'][1] = copy.deepcopy(doc['variants'][0])
    elif fault == 'unreviewed':
        doc['variants'][0]['review']['face'] = False
    elif fault == 'missing_file':
        (tmp_path / '0.png').unlink()
    else:
        p = tmp_path / '0.png';data = p.read_bytes();p.write_bytes(data[:16] + struct.pack('>II', 720, 1280) + data[24:])
    assert v.validate(doc, tmp_path)


def test_quantidade_explicita(tmp_path):
    doc = package(tmp_path);doc['variants'].pop();doc['expected_variants'] = 2
    assert v.validate(doc, tmp_path)
    doc['count_reason'] = 'Usuário pediu somente duas nesta tarefa.'
    assert not v.validate(doc, tmp_path)


@pytest.mark.parametrize('prompt,active', [('Crie três thumbs do Jev', True), ('Melhore as miniaturas', True), ('Crie uma capa de vídeo no YouTube', True), ('Qual o saldo do canal?', False), ('Corrija o CSS do painel', False)])
def test_hook_injeta_contexto_sem_bloquear(prompt, active):
    run = subprocess.run([sys.executable, str(ROOT / '.claude/hooks/thumbs-contexto.py')], input=json.dumps({'prompt': prompt}), capture_output=True, text=True)
    assert run.returncode == 0
    if active:
        result = json.loads(run.stdout)
        assert result['hookSpecificOutput']['hookEventName'] == 'UserPromptSubmit'
        assert 'decision' not in result and 'permissionDecision' not in result['hookSpecificOutput']
    else:
        assert not run.stdout


def test_evento_malformado_nao_interrompe_prompt():
    run = subprocess.run([sys.executable, str(ROOT / '.claude/hooks/thumbs-contexto.py')], input='invalid', capture_output=True, text=True)
    assert run.returncode == 0 and not run.stdout
