import argparse
import array
import hashlib
import json
import math
import shutil
import subprocess
import tempfile
import time
import wave
from pathlib import Path
from urllib.parse import urlparse

import imageio_ffmpeg
import requests
from PIL import Image

from presenter_pilot import BudgetLedger

SPACE = 'loganblack0/musetalk-1-5'
REVISION = '1bd58b7748557839bb585cb8ab6dd1399b80fcf9'
HOST = 'https://loganblack0-musetalk-1-5.hf.space'
TEXT = 'Hallo, hier spricht Jonas.'
ATTEMPT = 'hf_musetalk15_jonas_speech_once'
REEL = 'presenter_pilot_20261114_v1'


def safe_url(url, host):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.netloc != host or parsed.username or parsed.password:
        raise ValueError('Unexpected media URL; refusing authenticated or cross-host access')
    return url


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


def download(session, url, path, host, limit):
    safe_url(url, host)
    with session.get(url, stream=True, timeout=(15, 60), allow_redirects=False) as response:
        if response.status_code != 200:
            raise ValueError('Media download did not return HTTP 200')
        with path.open('xb') as output:
            total = 0
            for chunk in response.iter_content(65536):
                total += len(chunk)
                if total > limit:
                    raise ValueError('Media exceeds size limit')
                output.write(chunk)
    return total


def gpu_seconds(duration):
    if not math.isfinite(duration) or not 0 < duration <= 4:
        raise ValueError('Only a measured audio clip of at most four seconds is allowed')
    return max(60, min(600, int(45 + duration * 18)))


def prepare(source, directory):
    directory.mkdir(parents=True, exist_ok=False)
    with Image.open(source) as image:
        if image.size != (576, 1024):
            raise ValueError('This reviewed crop requires the 576x1024 Jonas portrait')
        image.convert('RGB').save(directory / 'presenter_master.png')
        image.convert('RGB').crop((72, 0, 504, 768)).save(directory / 'presenter_crop.png')
    session = requests.Session()
    session.trust_env = False
    response = session.post('https://ffmpeg.mafrapi.eu/api/tts/edge', json={
        'text': TEXT, 'voice': 'de-DE-FlorianMultilingualNeural',
    }, timeout=(15, 60))
    response.raise_for_status()
    url = response.json()['voice_url']
    download(session, url, directory / 'speech.mp3', 'ffmpeg.mafrapi.eu', 5_000_000)
    subprocess.run([
        imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-n', '-v', 'error',
        '-i', str(directory / 'speech.mp3'), '-ar', '16000', '-ac', '1', str(directory / 'speech.wav'),
    ], check=True, capture_output=True, timeout=30)
    with wave.open(str(directory / 'speech.wav')) as audio:
        duration = audio.getnframes() / audio.getframerate()
    manifest = {
        'space': SPACE, 'revision': REVISION, 'attempt_id': ATTEMPT, 'reel_id': REEL,
        'text': TEXT, 'voice': 'de-DE-FlorianMultilingualNeural',
        'audio_duration_seconds': duration, 'max_gpu_seconds': gpu_seconds(duration),
        'crop': [72, 0, 504, 768], 'dimensions': [432, 768],
        'files': {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                  for name in ('presenter_master.png', 'presenter_crop.png', 'speech.mp3', 'speech.wav')},
        'status': 'prepared', 'production_approved': False,
        'commercial_dependency_review': 'pending', 'authentication': 'anonymous_no_payment_credentials',
    }
    save_json(directory / 'manifest.json', manifest)
    return manifest


def stage_existing_test_inputs(directory):
    path = directory / 'manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    for name in ('speech.wav', 'presenter_crop.png'):
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != manifest['files'][name]:
            raise ValueError('Test inputs changed')
    session = requests.Session()
    session.trust_env = False
    with (directory / 'speech.wav').open('rb') as audio, (directory / 'presenter_crop.png').open('rb') as image:
        response = session.post(HOST + '/gradio_api/upload', files=[
            ('files', ('speech.wav', audio, 'audio/wav')),
            ('files', ('presenter_crop.png', image, 'image/png')),
        ], timeout=(15, 60))
    response.raise_for_status()
    paths = response.json()
    if not isinstance(paths, list) or len(paths) != 2 or not all(isinstance(p, str) and p.startswith('/tmp/gradio/') for p in paths):
        raise ValueError('Unexpected upload response')
    relay = {'purpose': 'Re-stage the same already-public fictional test inputs; upload only, no generation',
             'audio_url': HOST + '/gradio_api/file=' + paths[0],
             'image_url': HOST + '/gradio_api/file=' + paths[1]}
    manifest['test_input_relay'] = relay
    save_json(path, manifest)
    return relay


def request_profile(manifest):
    attempt = manifest.get('attempt_id')
    profiles = {ATTEMPT: 0, 'hf_musetalk15_jonas_alignment_v1': -83}
    shift = manifest.get('bbox_shift', 0)
    if manifest.get('reel_id') != REEL or attempt not in profiles or type(shift) is not int or shift != profiles[attempt]:
        raise ValueError('Unknown attempt or unreviewed face-alignment profile')
    return attempt, shift


def prepare_alignment(source, directory):
    original = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    evidence = json.loads((source / 'alignment.json').read_text(encoding='utf-8'))
    if original.get('status') != 'complete' or evidence['bbox_shift_candidate'] != -83:
        raise ValueError('Reviewed baseline and matching CPU alignment evidence required')
    manifest = {key: original[key] for key in ('space', 'revision', 'reel_id', 'text', 'voice',
                'audio_duration_seconds', 'max_gpu_seconds', 'crop', 'dimensions', 'files',
                'production_approved', 'commercial_dependency_review', 'authentication')}
    manifest.update(status='prepared', attempt_id='hf_musetalk15_jonas_alignment_v1', bbox_shift=-83,
                    comparison_baseline=str(source), alignment_evidence=evidence)
    request_profile(manifest)
    for name, checksum in manifest['files'].items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != checksum:
            raise ValueError('Baseline inputs changed')
    directory.mkdir(parents=True, exist_ok=False)
    for name in manifest['files']:
        shutil.copyfile(source / name, directory / name)
    save_json(directory / 'manifest.json', manifest)
    return manifest


def submit(directory, database):
    path = directory / 'manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    if manifest['status'] != 'prepared':
        raise ValueError('Submission already attempted; do not resubmit')
    attempt, shift = request_profile(manifest)
    gpu_seconds(manifest['audio_duration_seconds'])
    for name, checksum in manifest['files'].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != checksum:
            raise ValueError('Prepared media changed; submission blocked')
    session = requests.Session()
    session.trust_env = False
    runtime = session.get('https://huggingface.co/api/spaces/' + SPACE, timeout=20)
    runtime.raise_for_status()
    info = runtime.json()
    if info.get('sha') != REVISION or info.get('runtime', {}).get('stage') != 'RUNNING' or info.get('runtime', {}).get('hardware', {}).get('current') != 'zero-a10g':
        raise ValueError('Reviewed ZeroGPU Space revision is not running')
    ledger = BudgetLedger(database)
    if not ledger.reserve(REEL, attempt, 100):
        raise ValueError('Attempt already reserved; automatic resubmission blocked')
    manifest['status'] = 'reserved'
    save_json(path, manifest)
    submitted = False
    try:
        with (directory / 'speech.wav').open('rb') as audio, (directory / 'presenter_crop.png').open('rb') as image:
            upload = session.post(HOST + '/gradio_api/upload', files=[
                ('files', ('speech.wav', audio, 'audio/wav')),
                ('files', ('presenter_crop.png', image, 'image/png')),
            ], timeout=(15, 60))
        upload.raise_for_status()
        paths = upload.json()
        if not isinstance(paths, list) or len(paths) != 2 or not all(isinstance(p, str) and p.startswith('/tmp/gradio/') for p in paths):
            raise ValueError('Invalid upload response')
        files = [{'path': p, 'meta': {'_type': 'gradio.FileData'}} for p in paths]
        manifest['status'] = 'submitting'
        save_json(path, manifest)
        submitted = True
        response = session.post(HOST + '/gradio_api/call/generate', json={
            'data': [files[0], files[1], shift, 10, 'jaw', 90, 90],
        }, timeout=(15, 30))
        response.raise_for_status()
        event_id = response.json().get('event_id')
        if not isinstance(event_id, str) or len(event_id) != 32 or any(c not in '0123456789abcdef' for c in event_id):
            raise ValueError('No valid event ID; do not resubmit')
        manifest.update(status='submitted', event_id=event_id)
        save_json(path, manifest)
        return read_result(directory, session)
    except Exception:
        manifest = json.loads(path.read_text(encoding='utf-8'))
        if manifest['status'] != 'complete':
            manifest['status'] = 'unknown' if submitted else 'failed_before_submission'
            save_json(path, manifest)
            ledger.settle(REEL, attempt, actual_cents=None if submitted else 0, outcome='unknown' if submitted else 'failed')
        raise


def read_result(directory, session=None):
    session = session or requests.Session()
    session.trust_env = False
    path = directory / 'manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    event_id = manifest['event_id']
    if len(event_id) != 32 or any(c not in '0123456789abcdef' for c in event_id):
        raise ValueError('Invalid persisted event ID')
    deadline = time.monotonic() + 240
    event = ''
    with session.get(HOST + '/gradio_api/call/generate/' + event_id, stream=True, timeout=(15, 150)) as response:
        response.raise_for_status()
        for line in response.iter_lines(decode_unicode=True):
            if time.monotonic() > deadline:
                raise TimeoutError('Result deadline reached; do not resubmit')
            if line.startswith('event:'):
                event = line[6:].strip()
            elif line.startswith('data:') and event == 'error':
                manifest['provider_error'] = json.loads(line[5:].strip())
                save_json(path, manifest)
                raise RuntimeError('Provider returned an error; inspect persisted provider_error, no automatic retry')
            elif line.startswith('data:') and event == 'complete':
                data = json.loads(line[5:].strip())
                manifest['provider_result'] = data
                save_json(path, manifest)
                url = data[0]['video']['url']
                download(session, url, directory / 'speaker_test.mp4', 'loganblack0-musetalk-1-5.hf.space', 50_000_000)
                manifest['status'] = 'complete'
                save_json(path, manifest)
                return manifest
    raise ValueError('Stream ended without a complete result')


def validate_metrics(width, height, frames, fps, audio_duration, expected_duration):
    if not all(math.isfinite(value) for value in (width, height, frames, fps, audio_duration, expected_duration)) or audio_duration <= 0 or expected_duration <= 0:
        raise ValueError('Known positive measured durations and finite media metrics are required')
    if width <= 0 or height <= 0 or width * 16 != height * 9:
        raise ValueError('Expected an actual 9:16 video without resolution claims')
    if not math.isfinite(fps) or fps <= 0 or frames < 2:
        raise ValueError('Invalid or incomplete video stream')
    duration = frames / fps
    if abs(duration - expected_duration) > 0.2 or abs(audio_duration - expected_duration) > 0.2:
        raise ValueError('Audio/video duration differs from measured narration')
    return duration


def inspect_result(directory, database):
    import cv2

    path = directory / 'manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    video = directory / 'speaker_test.mp4'
    executable = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([executable, '-nostdin', '-v', 'error', '-i', str(video),
                    '-map', '0:v:0', '-map', '0:a:0', '-f', 'null', '-'],
                   check=True, capture_output=True, timeout=60)
    capture = cv2.VideoCapture(str(video))
    try:
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = capture.get(cv2.CAP_PROP_FPS)
        with tempfile.TemporaryDirectory() as temp:
            audio_file = Path(temp) / 'decoded.wav'
            subprocess.run([executable, '-nostdin', '-n', '-v', 'error', '-i', str(video),
                            '-map', '0:a:0', '-ar', '16000', '-ac', '1', str(audio_file)],
                           check=True, capture_output=True, timeout=30)
            with wave.open(str(audio_file)) as audio:
                audio_duration = audio.getnframes() / audio.getframerate()
                samples = array.array('h', audio.readframes(audio.getnframes()))
        rms = math.sqrt(sum(s * s for s in samples) / max(1, len(samples)))
        if rms < 100:
            raise ValueError('Narration is missing or nearly silent')
        duration = validate_metrics(width, height, frames, fps, audio_duration, manifest['audio_duration_seconds'])
        sheet = Image.new('RGB', (810, 480))
        for index, frame_number in enumerate((0, frames // 2, frames - 1)):
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ok, frame = capture.read()
            if not ok:
                raise ValueError('Unable to decode required beginning/middle/end frame')
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            sheet.paste(image.resize((270, 480)), (index * 270, 0))
        sheet.save(directory / 'contact_sheet.jpg')
    finally:
        capture.release()
    manifest['media_validation'] = {
        'decoder': 'FFmpeg full video and audio decode plus OpenCV metadata; ffprobe not available locally',
        'width': width, 'height': height, 'frames': frames, 'fps': fps,
        'video_duration_seconds': duration, 'audio_duration_seconds': audio_duration,
        'narration_rms_pcm16': rms, 'quality_status': 'pending_visual_and_auditory_review',
    }
    manifest['actual_incremental_cost_cents'] = 0
    manifest['billing_evidence'] = 'Anonymous public ZeroGPU request without HF token or payment credentials; no paid fallback'
    save_json(path, manifest)
    BudgetLedger(database).settle(REEL, request_profile(manifest)[0], actual_cents=0, outcome='accepted')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['prepare', 'align', 'stage', 'submit', 'result', 'inspect'])
    parser.add_argument('--directory', type=Path, default=Path('output/presenter_lipsync_jonas'))
    parser.add_argument('--source', type=Path)
    parser.add_argument('--database', default='output/presenter_pilot_budget.sqlite')
    args = parser.parse_args()
    if args.operation == 'prepare':
        result = prepare(args.source, args.directory)
    elif args.operation == 'align':
        result = prepare_alignment(args.source, args.directory)
    elif args.operation == 'stage':
        result = stage_existing_test_inputs(args.directory)
    elif args.operation == 'submit':
        result = submit(args.directory, args.database)
    elif args.operation == 'inspect':
        result = inspect_result(args.directory, args.database)
    else:
        result = read_result(args.directory)
    print(json.dumps(result, indent=2, ensure_ascii=False))
