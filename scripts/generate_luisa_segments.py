"""Generate measured German Luisa (Chatterbox) segments for the skincare pilot.

Uses the public ResembleAI/Chatterbox-Multilingual-TTS Space with the configured
clone reference. One batch attempt; no automatic retry per segment.
"""
import json
import subprocess
import sys
import time
import wave
from pathlib import Path

import imageio_ffmpeg
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from presenter_longcat_pilot import runtime_token  # noqa: E402

HOST = 'https://resembleai-chatterbox-multilingual-tts.hf.space'
CLONE_REFERENCE_URL = 'https://files.catbox.moe/b76w25.mp3'
SETTINGS = {'language_id': 'de', 'exaggeration': 0.72, 'temperature': 0.8,
            'seed': 72, 'cfg_weight': 0.05}
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def ffmpeg_wav(source, target):
    subprocess.run([FFMPEG, '-y', '-i', str(source), '-ar', '16000', '-ac', '1', str(target)],
                   check=True, capture_output=True)


def wav_seconds(path):
    with wave.open(str(path), 'rb') as audio:
        return audio.getnframes() / audio.getframerate()


def main():
    product = json.loads(Path('output/selected_pilot_product.json').read_text(encoding='utf-8'))
    scenes = product['script_draft']['scenes']
    out = Path('output/luisa_segments')
    out.mkdir(parents=True, exist_ok=True)

    token = runtime_token('hf_token.txt')
    session = requests.Session()
    session.trust_env = False
    auth = {'Authorization': 'Bearer ' + token}

    reference = out / 'clone_reference.mp3'
    if not reference.exists():
        response = session.get(CLONE_REFERENCE_URL, timeout=60)
        response.raise_for_status()
        reference.write_bytes(response.content)

    with reference.open('rb') as handle:
        uploaded = session.post(HOST + '/gradio_api/upload', headers=auth,
                                files={'files': ('reference.mp3', handle, 'audio/mpeg')}, timeout=60)
    uploaded.raise_for_status()
    reference_path = uploaded.json()[0]
    print('reference uploaded', reference_path)

    results = []
    for scene in scenes:
        scene_id = scene['scene_id']
        target = out / (scene_id + '.wav')
        if target.exists():
            results.append({'scene_id': scene_id, 'seconds': wav_seconds(target), 'resumed': True})
            continue
        payload = {'data': [scene['text'], SETTINGS['language_id'],
                            {'path': reference_path, 'meta': {'_type': 'gradio.FileData'}},
                            SETTINGS['exaggeration'], SETTINGS['temperature'],
                            SETTINGS['seed'], SETTINGS['cfg_weight']]}
        call = session.post(HOST + '/gradio_api/call/generate_tts_audio', headers=auth,
                            json=payload, timeout=30)
        call.raise_for_status()
        event_id = call.json()['event_id']
        (out / (scene_id + '.event.json')).write_text(json.dumps({'event_id': event_id}))
        stream = session.get(HOST + '/gradio_api/call/generate_tts_audio/' + event_id,
                             headers=auth, timeout=600)
        stream.raise_for_status()
        audio_url = None
        for line in stream.text.splitlines():
            if line.startswith('data: '):
                data = json.loads(line[6:])
                if data and isinstance(data[0], dict):
                    audio_url = data[0].get('url') or data[0].get('path')
        if not audio_url or not audio_url.startswith(HOST):
            raise ValueError('Unexpected TTS result for ' + scene_id)
        audio = session.get(audio_url, headers=auth, timeout=120)
        audio.raise_for_status()
        raw = out / (scene_id + '_raw' + Path(audio_url.split('?')[0]).suffix)
        raw.write_bytes(audio.content)
        ffmpeg_wav(raw, target)
        seconds = wav_seconds(target)
        print(scene_id, round(seconds, 3), 's')
        results.append({'scene_id': scene_id, 'role': scene['role'], 'visual': scene['visual'],
                        'text': scene['text'], 'seconds': seconds, 'event_id': event_id})
        time.sleep(1)

    manifest = {'provider': 'ResembleAI/Chatterbox-Multilingual-TTS', 'settings': SETTINGS,
                'clone_reference_url': CLONE_REFERENCE_URL,
                'segments': results, 'production_approved': False}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(json.dumps(manifest['segments'], indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
