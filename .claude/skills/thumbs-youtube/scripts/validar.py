"""Validação local, sem rede ou mutações. Revisão visual é declarada pelo revisor, não inferida."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path


def dimensions(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n') and data[12:16] == b'IHDR':
        return struct.unpack('>II', data[16:24])
    if data[:2] == b'\xff\xd8':
        pos = 2
        while pos < len(data):
            if data[pos] != 255:
                break
            while pos < len(data) and data[pos] == 255:
                pos += 1
            marker = data[pos]
            pos += 1
            if marker in (0xD9, 0xDA):
                break
            if marker in range(0xD0, 0xD9) or marker == 1:
                continue
            size = struct.unpack('>H', data[pos:pos+2])[0]
            if size < 2:
                break
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack('>HH', data[pos+3:pos+7])
                return w, h
            pos += size
    raise ValueError('cabeçalho JPG/PNG inválido ou não suportado')


def asset(root, name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError('caminho ausente')
    path = (root / name).resolve()
    if path.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.svg'):
        raise ValueError('arquivo deve ser uma imagem')
    return path.read_bytes()


def fingerprint(doc, item, root):
    shared = {k: doc.get(k) for k in ('tool', 'brand', 'identity')}
    content = {k: v for k, v in item.items() if k != 'review'}
    payload = {'shared': shared, 'variant': content,
               'image': hashlib.sha256(asset(root, item.get('file'))).hexdigest()}
    logo = doc.get('brand', {}).get('logo')
    if logo:
        payload['logo'] = hashlib.sha256(asset(root, logo)).hexdigest()
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate(doc, root):
    errors = []
    def check(ok, message):
        if not ok:
            errors.append(message)
    if not isinstance(doc, dict):
        return ['manifesto deve ser objeto']
    check(doc.get('version') == 1, 'version deve ser 1')
    count = doc.get('expected_variants', 3)
    check(type(count) is int and 1 <= count <= 16, 'quantidade inválida')
    check(count == 3 or bool(doc.get('count_reason')), 'quantidade diferente de 3 exige pedido registrado')
    tool = doc.get('tool')
    check(isinstance(tool, str) and bool(tool.strip()), 'nome da ferramenta ausente')
    brand = doc.get('brand')
    if not isinstance(brand, dict):
        return errors + ['brand deve ser objeto']
    check(isinstance(brand.get('source'), str) and brand['source'].startswith('https://'), 'fonte oficial ausente')
    colors = brand.get('colors')
    check(isinstance(colors, list) and bool(colors) and all(isinstance(c, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', c) for c in colors), 'paleta ausente/inválida')
    check(bool(brand.get('logo_note')), 'origem ou ausência do logo não documentada')
    identity = doc.get('identity')
    check(isinstance(identity, dict) and bool(identity.get('method')) and 'reference' in identity, 'procedência da identidade ausente')
    variants = doc.get('variants')
    if not isinstance(variants, list):
        return errors + ['variants deve ser lista']
    check(len(variants) == count, f'esperadas {count} variantes')
    seen = {k: set() for k in ('id', 'title', 'concept', 'image')}
    for i, item in enumerate(variants, 1):
        prefix = f'variante {i}: '
        if not isinstance(item, dict):
            errors.append(prefix + 'deve ser objeto')
            continue
        for key in ('id', 'title', 'headline', 'concept', 'evidence', 'file'):
            val = item.get(key)
            check(isinstance(val, str) and bool(val.strip()), prefix + key + ' ausente')
            if key in seen and isinstance(val, str):
                val = val.strip().casefold()
                check(val not in seen[key], prefix + key + ' duplicado')
                seen[key].add(val)
        if isinstance(tool, str) and tool.strip():
            for key in ('title', 'headline'):
                check(bool(re.search(r'(?<!\w)' + re.escape(tool.strip()) + r'(?!\w)', str(item.get(key, '')), re.I)), prefix + f'{key} sem nome da ferramenta')
        try:
            data = asset(root, item.get('file'))
            check(dimensions(data) == (1280, 720), prefix + 'exportar em 1280x720')
            check(len(data) < 2_000_000, prefix + 'arquivo deve ter menos de 2 MB')
            digest = hashlib.sha256(data).hexdigest()
            check(digest not in seen['image'], prefix + 'imagem idêntica a outra variante')
            seen['image'].add(digest)
            expected = fingerprint(doc, item, root)
        except (OSError, ValueError, TypeError, IndexError, struct.error) as e:
            errors.append(prefix + str(e))
            continue
        review = item.get('review')
        if not isinstance(review, dict):
            errors.append(prefix + 'revisão visual ausente')
            continue
        check(review.get('fingerprint') == expected, prefix + 'revisão ausente ou desatualizada')
        check(bool(review.get('reviewer')) and bool(review.get('notes')), prefix + 'revisor e observações obrigatórios')
        for key in ('face', 'text', 'brand', 'composition', 'feed'):
            check(review.get(key) is True, prefix + 'conferir visualmente ' + key)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['validar', 'fingerprints'])
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    try:
        doc = json.loads(args.manifest.read_text())
        if args.command == 'fingerprints':
            result = {v['id']: fingerprint(doc, v, args.manifest.parent) for v in doc['variants']}
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        errors = validate(doc, args.manifest.parent)
        print(json.dumps({'ok': not errors, 'errors': errors, 'visual_review': 'declarada pelo revisor; não inferida pelo script'}, ensure_ascii=False, indent=2))
        return 1 if errors else 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError, struct.error) as e:
        print(json.dumps({'ok': False, 'errors': [str(e)]}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
