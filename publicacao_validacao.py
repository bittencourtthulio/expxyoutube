"""Preflight determinístico da aula: metadados do MP4, capítulos e estrutura/tempos do SRT."""
import json
import math
import re
import subprocess
from fractions import Fraction


def probe_video(path):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries',
             'format=duration:stream=codec_type,width,height,display_aspect_ratio:stream_side_data=rotation',
             '-of', 'json', str(path)], capture_output=True, text=True, timeout=30, check=True)
    except FileNotFoundError as exc:
        raise ValueError('ffprobe ausente; instalar/conferir a ferramenta antes de enviar') from exc
    except (subprocess.SubprocessError, OSError) as exc:
        raise ValueError('ffprobe não conseguiu ler o vídeo final') from exc
    return video_metadata(json.loads(result.stdout))


def video_metadata(data):
    videos = [s for s in data.get('streams', []) if s.get('codec_type') == 'video']
    if len(videos) != 1 or not any(s.get('codec_type') == 'audio' for s in data.get('streams', [])):
        raise ValueError('MP4 deve conter um vídeo e áudio da aula')
    v = videos[0]
    width, height = int(v.get('width', 0)), int(v.get('height', 0))
    if width <= 0 or height <= 0:
        raise ValueError('dimensões do vídeo inválidas')
    aspect = v.get('display_aspect_ratio')
    ratio = float(Fraction(aspect.replace(':', '/'))) if aspect and aspect != '0:1' else width / height
    rotation = next((float(s['rotation']) for s in v.get('side_data_list', []) if 'rotation' in s), 0)
    if abs(rotation) % 180 == 90:
        width, height, ratio = height, width, 1 / ratio
    if not math.isclose(ratio, 16 / 9, rel_tol=0.005) or height < 720:
        raise ValueError('esperada aula horizontal 16:9 em HD (mínimo 720p)')
    duration = float(data.get('format', {}).get('duration', 0))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('duração do MP4 inválida')
    return {'width': width, 'height': height, 'duration_seconds': duration, 'audio': True}


def chapters(description, duration):
    result = []
    for line in description.splitlines():
        match = re.fullmatch(r'(\d{1,3}:\d{2}(?::\d{2})?)\s+(\S.*)', line.strip())
        if not match:
            continue
        stamp, title = match.groups()
        parts = list(map(int, stamp.split(':')))
        if any(p >= 60 for p in parts[1:]):
            raise ValueError('timestamp de capítulo inválido: ' + stamp)
        seconds = sum(n * 60 ** i for i, n in enumerate(reversed(parts)))
        result.append({'timestamp': stamp, 'seconds': seconds, 'title': title})
    if len(result) < 3 or result[0]['seconds'] != 0:
        raise ValueError('capítulos precisam de pelo menos três entradas, começando em 00:00')
    bounds = [c['seconds'] for c in result] + [duration]
    if any(b - a < 10 for a, b in zip(bounds, bounds[1:])):
        raise ValueError('capítulos devem ser crescentes, durar pelo menos 10 s e caber no vídeo')
    return result


def captions(text, duration):
    blocks = re.split(r'\n\s*\n', text.lstrip('\ufeff').replace('\r\n', '\n').strip())
    previous_start, end = -1, 0
    pattern = r'(\d{2,}):([0-5]\d):([0-5]\d),(\d{3})'
    for number, block in enumerate(blocks, 1):
        lines = block.splitlines()
        if len(lines) < 3 or lines[0].strip() != str(number) or not ''.join(lines[2:]).strip():
            raise ValueError(f'SRT inválido no bloco {number}: índice, timestamp ou texto ausente')
        match = re.fullmatch(pattern + r' --> ' + pattern, lines[1].strip())
        if not match:
            raise ValueError(f'SRT inválido no timestamp do bloco {number}')
        nums = list(map(int, match.groups()))
        start, end = [h * 3600 + m * 60 + s + ms / 1000 for h, m, s, ms in (nums[:4], nums[4:])]
        # Sobreposição de falas pode ser válida; rejeitar ordem invertida, não sobreposição.
        if start < previous_start or end <= start or end > duration + 0.5:
            raise ValueError(f'SRT fora de ordem/duração no bloco {number}')
        previous_start = start
    return {'cues': len(blocks), 'last_end_seconds': end,
            'semantic_review': 'estrutura e tempos válidos; correspondência com a fala exige revisão'}


def validate_media(video, description, srt):
    metadata = probe_video(video)
    duration = metadata['duration_seconds']
    return {'video': metadata, 'chapters': chapters(description, duration),
            'captions': captions(srt, duration)}
