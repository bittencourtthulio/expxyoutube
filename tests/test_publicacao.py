import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys

import pytest

import publicacao as pub


class Request:
    def __init__(self, fn): self.fn = fn
    def execute(self): return copy.deepcopy(self.fn())
    def next_chunk(self, num_retries=0): return None, copy.deepcopy(self.fn())


class API:
    def __init__(self):
        self.mutations = []
        self.channel_id = 'channel'
        self.v = None
        self.caps = []
        self.pl = []
        self.members = []
        self.delay = 0
        self.fail = None
    def __getattr__(self, resource):
        api = self
        class Resource:
            def list(self, **kw):
                def read():
                    if resource == 'channels': return {'items': [{'id': api.channel_id}]}
                    if resource == 'videos':
                        result = copy.deepcopy(api.v)
                        if api.delay:
                            api.delay -= 1
                            result['status'].pop('publishAt', None)
                        return {'items': [result] if result else []}
                    return {'items': copy.deepcopy({'captions': api.caps, 'playlists': api.pl, 'playlistItems': api.members}[resource])}
                return Request(read)
            def insert(self, **kw): return Request(lambda: api.write(resource, 'insert', kw))
            def update(self, **kw): return Request(lambda: api.write(resource, 'update', kw))
            def set(self, **kw): return Request(lambda: api.write(resource, 'set', kw))
        return Resource
    def write(self, resource, method, kw):
        self.mutations.append((resource, method, copy.deepcopy(kw.get('body'))))
        if self.fail == resource:
            raise TimeoutError('resultado remoto incerto')
        if resource == 'videos' and method == 'insert':
            self.v = dict(id='video', snippet={**kw['body']['snippet'], 'channelId': 'channel'}, status=kw['body']['status'],
                          processingDetails={'processingStatus': 'succeeded'}, contentDetails={'definition': 'hd', 'duration': 'PT7M53S'})
            return self.v
        if resource == 'videos':
            self.v['status'] = kw['body']['status'];self.delay = 2
            return self.v
        if resource == 'thumbnails':
            self.v['contentDetails']['hasCustomThumbnail'] = True
            return {'items': []}
        if resource == 'captions':
            self.caps = [{'id': 'caption', 'snippet': {'language': 'pt-BR', 'status': 'serving'}}]
            return self.caps[0]
        if resource == 'playlists':
            self.pl = [{'id': 'playlist', 'snippet': {**kw['body']['snippet'], 'channelId': 'channel'}}]
            return self.pl[0]
        self.members = [{'id': 'member', 'snippet': kw['body']['snippet']}]
        return self.members[0]


def loaded():
    future = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0).isoformat().replace('+00:00','Z')
    return {'fingerprint':'fixed', 'publish_at':future, 'description':'CTA\n00:00 Aula\n',
            'variants':[{'id':'01','title':'Jev: decisões'}],
            'assets':{'video':Path('video.mp4'),'thumb_01':Path('01.jpg'),'captions':Path('pt.srt')},
            'plan':{'alias':'alias','channel_id':'channel','made_for_kids':False,'contains_synthetic_media':True,
                    'playlist':{'title':'Série','description':'Aulas'}}}


def runner(tmp_path, api=None, data=None):
    data = data or loaded()
    return pub.Publisher(api or API(), data, pub.Journal(tmp_path/'state.json',data['fingerprint']), sleep=lambda _:None, media=lambda *a,**k:'media')


def test_upload_com_leitura_atrasada_e_retomada_sem_duplicar(tmp_path):
    p = runner(tmp_path)
    assert p.execute()['ok']
    before = copy.deepcopy(p.y.mutations)
    assert p.execute()['ok']
    assert p.y.mutations == before
    assert sum(r == 'videos' and op == 'insert' for r,op,_ in before) == 1
    assert sum(r == 'videos' and op == 'update' for r,op,_ in before) == 1
    assert p.j.data['verification']['ok']


def test_timeout_nao_repete_criacao(tmp_path):
    api = API();api.fail='videos';p=runner(tmp_path,api)
    with pytest.raises(TimeoutError): p.execute()
    assert p.j.data['pending'] == 'video_id'
    p2 = runner(tmp_path,api,p.l)
    with pytest.raises(ValueError, match='pendente'): p2.execute()
    assert len(api.mutations) == 1


def test_falha_depois_do_upload_preserva_id(tmp_path):
    api=API();api.fail='captions';p=runner(tmp_path,api)
    with pytest.raises(TimeoutError): p.execute()
    assert p.j.data['done']['video_id']=='video'
    with pytest.raises(ValueError): p.execute()
    assert sum(r=='videos' and op=='insert' for r,op,_ in api.mutations)==1


def test_canal_errado_impede_toda_mutacao(tmp_path):
    api=API();api.channel_id='outro'
    with pytest.raises(ValueError,match='canal'): runner(tmp_path,api).execute()
    assert not api.mutations


def test_data_passada_nao_envia(tmp_path):
    data=loaded();data['publish_at']='2000-01-01T00:00:00Z';p=runner(tmp_path,data=data)
    with pytest.raises(ValueError,match='passou'): p.execute()
    assert not p.y.mutations


def test_playlist_de_outro_canal_e_nome_duplicado(tmp_path):
    for playlist in ({'id':'playlist'}, {'title':'Série','description':'Aulas'}):
        api=API();api.pl=[{'id':'playlist','snippet':{'channelId':'outro','title':'Série'}}]
        data=loaded();data['plan']['playlist']=playlist;p=runner(tmp_path,api,data)
        with pytest.raises(ValueError): p.execute()
        assert not api.mutations


def test_status_preserva_flags_e_descarta_campos_somente_leitura():
    current={'privacyStatus':'private','embeddable':False,'publicStatsViewable':True,'license':'creativeCommon','madeForKids':True,'uploadStatus':'processed'}
    status=pub.schedule_status(current,loaded()['plan'],loaded()['publish_at'])
    assert status['embeddable'] is False and status['publicStatsViewable'] is True
    assert status['license']=='creativeCommon' and status['containsSyntheticMedia'] is True
    assert 'madeForKids' not in status and 'uploadStatus' not in status


def test_normalizacao_so_fim_de_linha():
    assert pub.normalized_description('CTA\r\n00:00 Aula\n')==pub.normalized_description('CTA\n00:00 Aula')
    assert pub.normalized_description('CTA\n00:00 Aula')!=pub.normalized_description('CTA 00:00 Aula')
    assert pub.normalized_description('CTA ' )!='CTA'


def test_fuso_sem_offset_e_offset_incorreto():
    assert pub.utc_time({'publish_local':'2026-09-28T10:00:00-03:00','timezone':'America/Sao_Paulo'})=='2026-09-28T13:00:00Z'
    for local in ('2026-09-28T10:00:00','2026-09-28T10:00:00-04:00'):
        with pytest.raises(ValueError): pub.utc_time({'publish_local':local,'timezone':'America/Sao_Paulo'})


def test_mudanca_hash_recusada(tmp_path):
    j=pub.Journal(tmp_path/'state.json','a');j.save()
    with pytest.raises(ValueError,match='mudaram'):pub.Journal(j.path,'b')


def test_verificacao_depois_da_data_so_consulta_e_aceita_titulo_aprovado(tmp_path):
    p = runner(tmp_path)
    p.l['variants'].append({'id': '02', 'title': 'Jev: outra abordagem'})
    assert p.execute()['ok']
    p.l['publish_at'] = '2000-01-01T00:00:00Z'
    before = copy.deepcopy(p.y.mutations)
    assert not p.verify()['ok']  # Ainda privado após a hora prometida: nunca publicar como correção.
    p.y.v['status'].update(privacyStatus='public')
    p.y.v['status'].pop('publishAt')
    p.y.v['snippet']['title'] = 'Jev: outra abordagem'
    assert p.verify()['ok']
    p.y.v['status']['embeddable'] = False
    assert not p.verify()['checks']['status_flags']
    p.y.v['snippet']['title'] = 'Título estranho'
    assert not p.verify()['checks']['title']
    assert p.y.mutations == before


@pytest.mark.parametrize('prompt,active', [('Agende esta aula para amanhã no YouTube',True),('Configure o teste AB',True),('Melhore o harness de publicação de vídeos',True),('Publique meu site',False),('Agende uma consulta médica',False),('Crie uma thumb',False)])
def test_hook_publicacao_nao_executa_nem_autoriza(prompt,active):
    script=pub.ROOT/'.claude/hooks/publicacao-contexto.py'
    r=subprocess.run([sys.executable,str(script)],input=json.dumps({'prompt':prompt}),capture_output=True,text=True)
    assert r.returncode==0
    if active:
        data=json.loads(r.stdout)
        assert 'decision' not in data
        assert data['hookSpecificOutput']['hookEventName']=='UserPromptSubmit'
    else: assert not r.stdout
