import copy

import pytest

from publicacao_validacao import captions, chapters, video_metadata


def metadata():
    return {'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080, 'display_aspect_ratio': '16:9'},
                        {'codec_type': 'audio'}], 'format': {'duration': '60'}}


def test_mp4_exige_horizontal_hd_audio_e_duracao():
    assert video_metadata(metadata())['duration_seconds'] == 60
    for invalid in ('portrait', 'rotation', 'audio', 'duration', 'sd'):
        m = copy.deepcopy(metadata())
        if invalid == 'portrait':
            m['streams'][0].update(width=1080, height=1920, display_aspect_ratio='9:16')
        elif invalid == 'rotation':
            m['streams'][0]['side_data_list'] = [{'rotation': 90}]
        elif invalid == 'audio': m['streams'].pop()
        elif invalid == 'duration': m['format']['duration'] = 'nan'
        else: m['streams'][0].update(width=640, height=360)
        with pytest.raises(ValueError): video_metadata(m)


def test_capitulos_crescentes_com_minimo_dez_segundos_inclusive_ultimo():
    result = chapters('CTA\n00:00 Abertura\n00:20 Prática\n00:40 Fechamento', 50)
    assert [c['seconds'] for c in result] == [0, 20, 40]
    assert chapters('00:00 A\n20:00 B\n01:00:00 C', 3610)[-1]['seconds'] == 3600


@pytest.mark.parametrize('text,duration', [
    ('00:00 A\n00:20 B', 60), ('00:01 A\n00:20 B\n00:40 C', 60),
    ('00:00 A\n00:05 B\n00:40 C', 60), ('00:00 A\n00:40 B\n00:20 C', 60),
    ('00:00 A\n00:20 B\n00:40 C', 49), ('00:00 A\n00:20 B\n00:40 C', 39),
    ('00:00 A\n00:20 B\n00:99 C', 180),
])
def test_rejeita_capitulos_invalidos(text, duration):
    with pytest.raises(ValueError): chapters(text, duration)


def test_srt_com_bom_crlf_e_sobreposicao_valida():
    result = captions('\ufeff1\r\n00:00:00,000 --> 00:00:12,000\r\nA\r\n\r\n2\r\n00:00:10,000 --> 00:00:20,000\r\nB', 30)
    assert result['cues'] == 2 and result['last_end_seconds'] == 20


@pytest.mark.parametrize('text', ['', '1\n00:00:00,000 --> 00:00:05,000',
    '2\n00:00:00,000 --> 00:00:05,000\nA', '1\n00:00:00,000 --> 00:00:31,000\nA',
    '1\n00:00:00,000 --> 00:00:00,000\nA', '1\n00:00:00,000 --> 00:00:99,000\nA',
    '1\n00:00:10,000 --> 00:00:15,000\nA\n\n2\n00:00:05,000 --> 00:00:20,000\nB'])
def test_rejeita_srt_sem_texto_fora_de_ordem_ou_duracao(text):
    with pytest.raises(ValueError): captions(text, 30)
