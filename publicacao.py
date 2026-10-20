"""Envio explícito de aulas; validar é local, verificar só consulta, enviar usa journal com lock."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from comum import gravar_json
from publicacao_validacao import validate_media

ROOT = Path(__file__).resolve().parent
WRITABLE_STATUS = ('license', 'embeddable', 'publicStatsViewable', 'selfDeclaredMadeForKids', 'containsSyntheticMedia')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def utc_time(plan):
    local = datetime.fromisoformat(plan['publish_local'])
    if local.tzinfo is None:
        raise ValueError('publish_local precisa de offset explícito; resolver horário/fuso com o usuário')
    zone = ZoneInfo(plan['timezone'])
    zoned = local.astimezone(zone)
    if zoned.replace(tzinfo=None) != local.replace(tzinfo=None) or zoned.utcoffset() != local.utcoffset():
        raise ValueError('offset e hora local não correspondem à zona IANA')
    return local.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def normalized_description(text):
    return text.replace('\r\n', '\n').rstrip('\n')


def load_plan(path):
    path = Path(path).resolve()
    plan = json.loads(path.read_text())
    for name in ('alias', 'channel_id', 'publish_local', 'timezone', 'authorization'):
        if not isinstance(plan.get(name), str) or not plan[name].strip():
            raise ValueError(f'{name} obrigatório')
    if not re.fullmatch(r'[\w-]+', plan['alias']):
        raise ValueError('alias inválido')
    for name in ('made_for_kids', 'contains_synthetic_media'):
        if type(plan.get(name)) is not bool:
            raise ValueError(f'{name} deve refletir o vídeo real, como booleano')
    assets = {}
    for name in ('video', 'description', 'captions', 'thumbs'):
        assets[name] = (path.parent / plan[name]).resolve()
        if not assets[name].is_file():
            raise ValueError(f'arquivo ausente: {name}')
    if assets['video'].suffix.lower() != '.mp4' or assets['captions'].suffix.lower() != '.srt':
        raise ValueError('esperados MP4 e SRT finais')
    spec = importlib.util.spec_from_file_location('thumbs_validator', ROOT / '.claude/skills/thumbs-youtube/scripts/validar.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    thumbs = json.loads(assets['thumbs'].read_text())
    errors = mod.validate(thumbs, assets['thumbs'].parent)
    if errors:
        raise ValueError('Pacote de thumbs: ' + '; '.join(errors))
    variants = thumbs['variants']
    for v in variants:
        if len(v['title']) > 100:
            raise ValueError('título ultrapassa 100 caracteres')
        assets['thumb_' + v['id']] = (assets['thumbs'].parent / v['file']).resolve()
    description = assets['description'].read_text()
    if not description.strip() or len(description) > 5000 or 'example.com' not in description.splitlines()[0].lower():
        raise ValueError('descrição inválida ou CTA Seu Site ausente no início')
    preflight = validate_media(assets['video'], description, assets['captions'].read_text())
    playlist = plan.get('playlist', {})
    if not isinstance(playlist, dict) or not (playlist.get('id') or (playlist.get('title') and playlist.get('description'))):
        raise ValueError('playlist precisa de id existente ou título e descrição para criação autorizada')
    hashes = {k: digest(v) for k, v in assets.items()}
    payload = json.dumps({'plan': plan, 'hashes': hashes}, sort_keys=True, ensure_ascii=False)
    return {'plan': plan, 'assets': assets, 'variants': variants, 'description': description, 'preflight': preflight,
            'publish_at': utc_time(plan), 'hashes': hashes,
            'fingerprint': hashlib.sha256(payload.encode()).hexdigest()}


def schedule_status(current, plan, publish_at):
    if current.get('privacyStatus') != 'private':
        raise ValueError('o vídeo deve estar privado; não alterar vídeo público automaticamente')
    result = {k: current[k] for k in WRITABLE_STATUS if k in current}
    result.update(privacyStatus='private', publishAt=publish_at,
                  selfDeclaredMadeForKids=plan['made_for_kids'],
                  containsSyntheticMedia=plan['contains_synthetic_media'])
    return result


class Journal:
    """Chamador mantém flock durante toda a execução; nunca apaga pending automaticamente."""
    def __init__(self, path, fingerprint):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {'fingerprint': fingerprint, 'done': {}}
        if self.data.get('fingerprint') != fingerprint:
            raise ValueError('plano/arquivos mudaram; reconciliar estado antes de continuar')
        if not isinstance(self.data.get('done'), dict):
            raise ValueError('journal inválido')

    def save(self):
        gravar_json(self.path, self.data)
        self.path.chmod(0o600)

    def once(self, key, action):
        if self.data.get('pending'):
            raise ValueError('resultado incerto; reconciliar antes de continuar: ' + self.data['pending'])
        if key in self.data['done']:
            return self.data['done'][key]
        self.data['pending'] = key
        self.save()
        value = action()
        self.data['done'][key] = value
        self.data.pop('pending')
        self.save()
        return value


def items(service, resource, **kwargs):
    """Paginar listas; não confundir primeira página com todos os recursos."""
    result, token = [], None
    while True:
        query = dict(kwargs)
        if token:
            query['pageToken'] = token
        page = getattr(service, resource)().list(**query).execute()
        result.extend(page.get('items', []))
        token = page.get('nextPageToken')
        if not token:
            return result


class Publisher:
    def __init__(self, youtube, loaded, journal, sleep=time.sleep, media=None):
        self.y = youtube
        self.l = loaded
        self.p = loaded['plan']
        self.j = journal
        self.sleep = sleep
        if media is None:
            from googleapiclient.http import MediaFileUpload
            media = MediaFileUpload
        self.media = media

    def channel(self):
        channels = items(self.y, 'channels', part='snippet', mine=True)
        if len(channels) != 1 or channels[0]['id'] != self.p['channel_id']:
            raise ValueError('canal autenticado difere do canal autorizado; nenhuma escrita permitida')
        return channels[0]

    def video(self):
        found = items(self.y, 'videos', part='snippet,status,contentDetails,processingDetails', id=self.j.data['done']['video_id'])
        if not found or found[0]['snippet']['channelId'] != self.p['channel_id']:
            raise ValueError('vídeo ausente ou de outro canal')
        return found[0]

    def verify(self):
        self.channel()
        v = self.video()
        done = self.j.data['done']
        due = datetime.fromisoformat(self.l['publish_at'].replace('Z', '+00:00')) <= datetime.now(timezone.utc)
        schedule_ok = (v['status'].get('privacyStatus') == 'public' if due else
                       v['status'].get('privacyStatus') == 'private' and v['status'].get('publishAt') == self.l['publish_at'])
        expected_flags = done.get('scheduled', {})
        checks = {
            'schedule': schedule_ok,
            'status_flags': all(v['status'].get(k) == expected_flags[k] for k in WRITABLE_STATUS
                                if k in expected_flags and k != 'containsSyntheticMedia'),
            'processing': v.get('processingDetails', {}).get('processingStatus') == 'succeeded',
            'hd': v.get('contentDetails', {}).get('definition') == 'hd',
            'duration': v.get('contentDetails', {}).get('duration') not in (None, 'P0D', 'PT0S'),
            'title': v['snippet']['title'] in [variant['title'] for variant in self.l['variants']],
            'description': normalized_description(v['snippet']['description']) == normalized_description(self.l['description']),
            'thumbnail': v.get('contentDetails', {}).get('hasCustomThumbnail') is True,
        }
        captions = items(self.y, 'captions', part='snippet', videoId=v['id'])
        checks['captions'] = any(x['id'] == done.get('caption_id') and x['snippet'].get('language') == self.p.get('language', 'pt-BR') and x['snippet'].get('status') == 'serving' for x in captions)
        playlist = done.get('playlist_id')
        checks['playlist'] = bool(playlist) and any(x['snippet']['resourceId']['videoId'] == v['id'] for x in items(self.y, 'playlistItems', part='snippet', playlistId=playlist, maxResults=50))
        return {'ok': all(checks.values()), 'checks': checks, 'video_id': v['id'], 'playlist_id': playlist,
                'publish_at': v['status'].get('publishAt'), 'privacy': v['status']['privacyStatus'],
                'expected_visibility': 'public' if due else 'scheduled', 'current_title': v['snippet']['title'],
                'processing': v.get('processingDetails', {}).get('processingStatus'),
                'checked_at': datetime.now(timezone.utc).isoformat(),
                'ab_test': 'não solicitado' if self.p.get('ab_test') is False else 'conferir no Studio; API não comprova experimento'}

    def execute(self):
        self.channel()
        if self.j.data.get('pending'):
            raise ValueError('reconciliar operação pendente: ' + self.j.data['pending'])
        done = self.j.data['done']
        if 'scheduled' not in done and datetime.fromisoformat(self.l['publish_at'].replace('Z', '+00:00')) <= datetime.now(timezone.utc):
            raise ValueError('data de publicação já passou; não publicar imediatamente por engano')
        playlist_plan = self.p['playlist']
        if 'playlist_id' not in done:
            if playlist_plan.get('id'):
                found = items(self.y, 'playlists', part='snippet', id=playlist_plan['id'])
                if not found or found[0]['snippet']['channelId'] != self.p['channel_id']:
                    raise ValueError('playlist não pertence ao canal autorizado')
            elif any(x['snippet']['title'] == playlist_plan['title'] for x in items(self.y, 'playlists', part='snippet', mine=True, maxResults=50)):
                raise ValueError('playlist com esse título já existe; conferir e usar id no plano')
        if 'video_id' in done and 'scheduled' not in done:
            if self.video()['status']['privacyStatus'] != 'private':
                raise ValueError('retomada encontrou vídeo não privado; reconciliar antes de alterar')
        language = self.p.get('language', 'pt-BR')
        def upload():
            request = self.y.videos().insert(part='snippet,status', notifySubscribers=self.p.get('notify_subscribers', True),
                body={'snippet': {'title': self.l['variants'][0]['title'], 'description': self.l['description'],
                                 'categoryId': self.p.get('category_id', '27'), 'defaultLanguage': language, 'defaultAudioLanguage': language},
                      'status': {'privacyStatus': 'private', 'selfDeclaredMadeForKids': self.p['made_for_kids'],
                                 'containsSyntheticMedia': self.p['contains_synthetic_media'], 'embeddable': True, 'publicStatsViewable': True}},
                media_body=self.media(str(self.l['assets']['video']), mimetype='video/mp4', chunksize=8*1024*1024, resumable=True))
            result = None
            while result is None:
                progress, result = request.next_chunk(num_retries=0)
                if progress:
                    print(f'Upload {round(progress.progress()*100)}%', flush=True)
            return result['id']
        video_id = self.j.once('video_id', upload)
        # Não tocar título/thumbnail de vídeo já agendado em uma retomada: pode interromper A/B.
        thumb = self.l['assets']['thumb_' + self.l['variants'][0]['id']]
        thumb_mime = 'image/png' if thumb.suffix.lower() == '.png' else 'image/jpeg'
        self.j.once('thumbnail', lambda: self.y.thumbnails().set(videoId=video_id, media_body=self.media(str(thumb), mimetype=thumb_mime)).execute())
        self.j.once('caption_id', lambda: self.y.captions().insert(part='snippet', body={'snippet': {'videoId': video_id, 'language': language, 'name': 'Português (Brasil)' if language == 'pt-BR' else language, 'isDraft': False}}, media_body=self.media(str(self.l['assets']['captions']), mimetype='application/octet-stream')).execute()['id'])
        playlist = self.p['playlist']
        def playlist_id():
            if playlist.get('id'):
                found = items(self.y, 'playlists', part='snippet', id=playlist['id'])
                if not found or found[0]['snippet']['channelId'] != self.p['channel_id']:
                    raise ValueError('playlist não pertence ao canal autorizado')
                return playlist['id']
            # Mesmo nome não basta para assumir identidade. Evitar criar duplicata sem decisão explícita.
            existing = items(self.y, 'playlists', part='snippet', mine=True, maxResults=50)
            if any(x['snippet']['title'] == playlist['title'] for x in existing):
                raise ValueError('playlist com esse título já existe; conferir e usar id no plano')
            return self.y.playlists().insert(part='snippet,status', body={'snippet': {'title': playlist['title'], 'description': playlist['description'], 'defaultLanguage': language}, 'status': {'privacyStatus': playlist.get('privacy', 'public')}}).execute()['id']
        pid = self.j.once('playlist_id', playlist_id)
        def associate():
            existing = items(self.y, 'playlistItems', part='snippet', playlistId=pid, maxResults=50)
            match = next((x for x in existing if x['snippet']['resourceId']['videoId'] == video_id), None)
            if match:
                return match['id']
            return self.y.playlistItems().insert(part='snippet', body={'snippet': {'playlistId': pid, 'resourceId': {'kind': 'youtube#video', 'videoId': video_id}}}).execute()['id']
        self.j.once('playlist_item_id', associate)
        def schedule():
            # Upload pode demorar: conferir relógio novamente imediatamente antes de agendar.
            if datetime.fromisoformat(self.l['publish_at'].replace('Z', '+00:00')) <= datetime.now(timezone.utc):
                raise ValueError('horário passou durante o envio; manter privado')
            status = schedule_status(self.video()['status'], self.p, self.l['publish_at'])
            return self.y.videos().update(part='status', body={'id': video_id, 'status': status}).execute()['status']
        self.j.once('scheduled', schedule)
        report = None
        for delay in (0, 2, 4, 8, 16):
            if delay:
                self.sleep(delay)
            report = self.verify()
            self.j.data['verification'] = report
            self.j.save()
            if report['ok']:
                break
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['validar', 'enviar', 'verificar'])
    parser.add_argument('plan', type=Path)
    parser.add_argument('--state', type=Path, help='journal exclusivo deste vídeo; obrigatório fora de validar')
    args = parser.parse_args()
    try:
        loaded = load_plan(args.plan)
        if args.command == 'validar':
            print(json.dumps({'ok': True, 'channel_id': loaded['plan']['channel_id'], 'publish_at': loaded['publish_at'], 'fingerprint': loaded['fingerprint'], 'local_only': True, 'preflight': loaded['preflight']}, ensure_ascii=False, indent=2))
            return 0
        if not args.state or args.state.resolve() == args.plan.resolve() or args.state.resolve() in loaded['assets'].values():
            raise ValueError('--state separado dos arquivos de entrada é obrigatório')
        if args.command == 'verificar' and not args.state.exists():
            raise ValueError('journal ausente; não há vídeo conhecido para verificar')
        from yt import Cliente
        if args.command == 'verificar':
            journal = Journal(args.state, loaded['fingerprint'])
            report = Publisher(Cliente.conectar(loaded['plan']['alias']).data, loaded, journal).verify()
        else:
            args.state.parent.mkdir(parents=True, exist_ok=True)
            with args.state.with_suffix(args.state.suffix + '.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                journal = Journal(args.state, loaded['fingerprint'])
                report = Publisher(Cliente.conectar(loaded['plan']['alias']).data, loaded, journal).execute()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report['ok'] else 2
    except Exception as exc:
        # Não imprimir payload/URL de upload/credenciais de bibliotecas externas.
        if isinstance(exc, (ValueError, FileNotFoundError)):
            message = str(exc)
        else:
            message = f'{type(exc).__name__}; consultar journal e reconciliar antes de repetir escrita'
        print(json.dumps({'ok': False, 'error': message}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
