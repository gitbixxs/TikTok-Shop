import argparse
import array
import getpass
import hashlib
import json
import math
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
import warnings
import wave
from contextlib import ExitStack, closing
from pathlib import Path
from urllib.parse import quote, urlparse

import imageio_ffmpeg
import requests
from PIL import Image

from presenter_lipsync_pilot import validate_metrics
from presenter_pilot import LONGCAT_MAX_AUDIO_SECONDS, BudgetLedger, build_manifest

SPACE = 'BizPunk/tiktok-longcat-worker'
HOST = 'https://bizpunk-tiktok-longcat-worker.hf.space'
REVISION = 'daeb7c18bdfd051b5f94a2e88287a50ccf2988e3'
PARAMETERS = {'resolution': '480p', 'seed': 72, 'vocal_mode': 'Clean speech (fast)', 'acceleration': 'Exact 8-step'}
DEFAULT_PROMPT = 'The same man from the reference image speaks naturally to the camera in the same kitchen. Preserve his identity, hairstyle, clothing and detailed beard texture. Subtle head movements and natural blinking. After the spoken sentence ends, he rests with his mouth gently closed. Static camera, no cuts, no new objects.'
MAX_AUDIO_SECONDS = LONGCAT_MAX_AUDIO_SECONDS
LIMITS = {'presenter.png': 2_000_000, 'speech.wav': 200_000}
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class LocalTokenError(ValueError):
    pass


def token_file_values(path):
    if not Path(path).is_file():
        raise LocalTokenError('Explicit token file is missing. Run configure-token --token-file .env in your own terminal first.')
    with Path(path).open(encoding='utf-8-sig') as source:
        text = source.read(65537)
    if len(text) > 65536:
        raise LocalTokenError('Explicit token file exceeds64KiB; no token loaded.')
    return re.findall(r'(?m)^[ \t]*(?:export[ \t]+)?HF_CREATIVE_TOKEN[ \t]*=(.*)$', text)


def runtime_token(token_file=None):
    if token_file is None:
        token = os.environ.get('HF_CREATIVE_TOKEN', '')
    else:
        values = token_file_values(token_file)
        if len(values) != 1:
            raise LocalTokenError('Explicit file must contain exactly one HF_CREATIVE_TOKEN assignment.')
        token = values[0].split('#', 1)[0].strip()
        if len(token) >= 2 and token[0] == token[-1] and token[0] in ('\"', "'"):
            token = token[1:-1]
    if not isinstance(token, str) or not re.fullmatch(r'hf_[A-Za-z0-9]{10,200}', token):
        raise LocalTokenError('No valid HF_CREATIVE_TOKEN. Use process environment or explicit --token-file .env; never send it in chat.')
    return token


def configure_runtime_token(token_file):
    if not sys.stdin.isatty():
        raise LocalTokenError('Run configure-token in your own interactive terminal, not an agent tool or redirected input.')
    requested = Path(token_file)
    root = PROJECT_ROOT.resolve()
    if requested.is_symlink() or requested.resolve() != root / '.env':
        raise LocalTokenError('Secure setup only supports this repository root .env; no other file is modified.')
    ignored = subprocess.run(['git', '-C', str(root), 'check-ignore', '--quiet', '--', '.env'],
                             capture_output=True, timeout=10)
    if ignored.returncode != 0:
        raise LocalTokenError('Refusing to store a token: .env must already be Git-ignored and untracked.')
    path = root / '.env'
    if path.exists() and path.stat().st_nlink != 1:
        raise LocalTokenError('Refusing to modify a linked secret file.')
    if path.exists() and token_file_values(path):
        runtime_token(path)
        return {'configured': True, 'already_present': True, 'token_file': str(path), 'inference_started': False}
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        token = getpass.getpass('Existing read-only HF_CREATIVE_TOKEN (hidden input): ')
    if not re.fullmatch(r'hf_[A-Za-z0-9]{10,200}', token):
        raise LocalTokenError('Invalid token format; no file modified.')
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(descriptor, 'a', encoding='utf-8', newline='\n') as output:
        output.write('\nHF_CREATIVE_TOKEN=' + token + '\n')
    return {'configured': True, 'already_present': False, 'token_file': str(path), 'inference_started': False}


def save(directory, manifest):
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=directory, delete=False) as output:
        temporary = Path(output.name)
        json.dump(manifest, output, indent=2, ensure_ascii=False)
    try:
        os.replace(temporary, directory / 'manifest.json')
    finally:
        temporary.unlink(missing_ok=True)


def load(directory):
    return json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))


def checksum(path, limit):
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError('Missing or oversized local media')
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(65536), b''):
            size += len(chunk)
            if size > limit:
                raise ValueError('Local media exceeded its limit')
            digest.update(chunk)
    return digest.hexdigest()


def audio_duration(path):
    with wave.open(str(path)) as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getcomptype()) != (1, 2, 16000, 'NONE'):
            raise ValueError('Narration must be mono PCM16 WAV at16kHz')
        frames = audio.getnframes()
        if not 0.2 <= frames / 16000 <= MAX_AUDIO_SECONDS:
            raise ValueError('Split narration into measured segments of0.2–4.8s; never truncate it')
        if len(audio.readframes(frames + 1)) != frames * 2:
            raise ValueError('Incomplete narration WAV')
    return frames / 16000


def validate_inputs(directory, manifest):
    if manifest.get('space') != SPACE or manifest.get('revision') != REVISION or manifest.get('parameters') != PARAMETERS:
        raise ValueError('Unreviewed provider profile')
    for key in ('reel_id', 'scene_id'):
        if not isinstance(manifest.get(key), str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', manifest[key]):
            raise ValueError('Stable local reel and scene identifiers are required')
    if manifest.get('attempt_id') != f"{manifest['reel_id']}:{manifest['scene_id']}:longcat15:v1":
        raise ValueError('Attempt identity changed')
    if not isinstance(manifest.get('prompt'), str) or not 1 <= len(manifest['prompt'].strip()) <= 2000 or not str(manifest.get('text', '')).strip():
        raise ValueError('Reviewed prompt and spoken text are required')
    if set(manifest.get('files', {})) != set(LIMITS):
        raise ValueError('Unexpected input files')
    for name, limit in LIMITS.items():
        if checksum(directory / name, limit) != manifest['files'][name]:
            raise ValueError('Prepared inputs changed; network submission blocked')
    duration = audio_duration(directory / 'speech.wav')
    if manifest.get('audio_duration_seconds') != duration:
        raise ValueError('Narration duration changed')
    with Image.open(directory / 'presenter.png') as image:
        width, height = image.size
        if image.format != 'PNG' or not 216 <= width <= 1080 or not 384 <= height <= 1920 or width * 16 != height * 9:
            raise ValueError('A reviewed native9:16 PNG presenter image is required')
        image.verify()
    return duration


def prepare(image, audio, directory, *, reel_id, scene_id, text, prompt=DEFAULT_PROMPT):
    directory = Path(directory)
    inputs = {'presenter.png': Path(image), 'speech.wav': Path(audio)}
    files = {name: checksum(path, LIMITS[name]) for name, path in inputs.items()}
    manifest = {'space': SPACE, 'revision': REVISION, 'reel_id': reel_id, 'scene_id': scene_id,
                'attempt_id': f'{reel_id}:{scene_id}:longcat15:v1', 'text': text, 'prompt': prompt,
                'parameters': dict(PARAMETERS), 'audio_duration_seconds': audio_duration(inputs['speech.wav']),
                'files': files, 'status': 'prepared', 'production_approved': False,
                'quality_status': 'pending_visual_and_auditory_review', 'commercial_dependency_review': 'pending'}
    directory.mkdir(parents=True, exist_ok=False)
    for name, source in inputs.items():
        with source.open('rb') as reader, (directory / name).open('xb') as writer:
            total = 0
            for chunk in iter(lambda: reader.read(65536), b''):
                total += len(chunk)
                if total > LIMITS[name]:
                    raise ValueError('Input grew while being prepared')
                writer.write(chunk)
    validate_inputs(directory, manifest)
    save(directory, manifest)
    return manifest


def prepare_scene(specification, scene_id, directory):
    manifest = build_manifest(specification)
    scene = next((scene for scene in manifest['scenes'] if scene['scene_id'] == scene_id), None)
    if scene is None or scene['visual'] != 'presenter' or scene.get('generation_provider') != 'longcat15':
        raise ValueError('An explicitly selected LongCat presenter scene is required')
    asset = next(asset for asset in manifest['assets'] if asset['asset_id'] == scene['asset_id'])
    checksum(Path(scene['audio_path']), LIMITS['speech.wav'])
    if abs(scene['voice_duration_sec'] - audio_duration(Path(scene['audio_path']))) > 1 / 16000:
        raise ValueError('Timeline and measured narration differ')
    prompt = scene.get('longcat_prompt')
    if not isinstance(prompt, str) or not prompt.strip() or prompt.strip() == DEFAULT_PROMPT.strip():
        raise ValueError('A scene-specific reviewed LongCat prompt is required; the male smoke-test default is not allowed')
    result = prepare(asset['local_path'], scene['audio_path'], directory,
                     reel_id=specification['reel_id'], scene_id=scene_id, text=scene['text'], prompt=prompt)
    result.update(product_key=manifest['product_key'], reference_asset_id=asset['asset_id'])
    save(Path(directory), result)
    return result


def validate_quota(quota):
    for key in ('current', 'overquotaUsed', 'observed_at'):
        if type(quota.get(key)) not in (int, float) or not math.isfinite(quota[key]):
            raise ValueError('Fresh operator-confirmed quota evidence is required')
    if quota['current'] < 600 or quota['overquotaUsed'] != 0 or not 0 <= time.time() - quota['observed_at'] <= 120 or quota.get('exclusive_use') is not True:
        raise ValueError('Need600 included seconds, no overage, no parallel jobs and evidence no older than120s')
    return quota['current']


def claim_quota(ledger, manifest, quota):
    evidence = hashlib.sha256(json.dumps(quota, sort_keys=True).encode()).hexdigest()
    with ledger.connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS longcat_quota_claims (evidence TEXT PRIMARY KEY, attempt_id TEXT NOT NULL)')
        try:
            db.execute('INSERT INTO longcat_quota_claims VALUES (?, ?)', (evidence, manifest['attempt_id']))
        except sqlite3.IntegrityError as error:
            raise ValueError('Quota evidence already used; refresh it before another job') from error
    return evidence


class MultipartUpload:
    def __init__(self, files):
        self.boundary = 'longcat-' + uuid.uuid4().hex
        self.stack = ExitStack()
        self.parts = []
        try:
            for path, mime in files:
                header = (f'--{self.boundary}\r\nContent-Disposition: form-data; name="files"; filename="{path.name}"\r\nContent-Type: {mime}\r\n\r\n').encode()
                self.parts.append((header, self.stack.enter_context(path.open('rb')), path.stat().st_size))
        except Exception:
            self.stack.close()
            raise
        self.tail = f'--{self.boundary}--\r\n'.encode()

    def __len__(self):
        return sum(len(header) + size + 2 for header, _, size in self.parts) + len(self.tail)

    def __iter__(self):
        for header, source, size in self.parts:
            yield header
            remaining = size
            while remaining:
                chunk = source.read(min(65536, remaining))
                if not chunk:
                    raise ValueError('Upload file changed')
                remaining -= len(chunk)
                yield chunk
            if source.read(1):
                raise ValueError('Upload file grew')
            yield b'\r\n'
        yield self.tail

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stack.close()


def auth(token):
    if not isinstance(token, str) or not token.strip() or any(character.isspace() for character in token):
        raise ValueError('Explicit private runtime token required in HF_CREATIVE_TOKEN')
    return {'Authorization': 'Bearer ' + token}


def bounded_content(response, limit, deadline=None):
    deadline = time.monotonic() + 120 if deadline is None else deadline
    if response.status_code != 200:
        raise ValueError('Expected HTTP200 without redirects')
    declared = response.headers.get('Content-Length')
    if isinstance(declared, str) and (not declared.isdigit() or int(declared) > limit):
        raise ValueError('Oversized or invalid response length')
    total = 0
    for chunk in response.iter_content(65536):
        if time.monotonic() > deadline:
            raise TimeoutError('Response deadline reached')
        total += len(chunk)
        if total > limit:
            raise ValueError('Response exceeds size limit')
        yield chunk


def request_json(session, method, url, token, **kwargs):
    headers = {**auth(token), **kwargs.pop('headers', {})}
    with session.request(method, url, headers=headers, stream=True, allow_redirects=False, timeout=(15, 60), **kwargs) as response:
        return json.loads(b''.join(bounded_content(response, 512_000)))


def preflight(session, token):
    info = request_json(session, 'GET', 'https://huggingface.co/api/spaces/' + SPACE, token)
    if (info.get('id'), info.get('host'), info.get('private'), info.get('sha')) != (SPACE, HOST, True, REVISION) or info.get('runtime', {}).get('stage') != 'RUNNING' or info.get('runtime', {}).get('hardware', {}).get('current') != 'zero-a10g':
        raise ValueError('Reviewed private ZeroGPU revision is not running')
    schema = request_json(session, 'GET', HOST + '/gradio_api/info', token)
    parameters = schema.get('named_endpoints', {}).get('/generate', {}).get('parameters', [])
    if [parameter.get('parameter_name') for parameter in parameters] != ['image_path', 'audio_path', 'prompt', *PARAMETERS]:
        raise ValueError('Private API signature changed')


def submit(directory, database, token, quota):
    directory = Path(directory)
    manifest = load(directory)
    if manifest.get('status') != 'prepared':
        raise ValueError('Submission already attempted; no automatic retry')
    validate_inputs(directory, manifest)
    auth(token)
    validate_quota(quota)
    quota = {key: quota[key] for key in ('current', 'overquotaUsed', 'observed_at', 'exclusive_use')}
    with closing(requests.Session()) as session:
        session.trust_env = False
        preflight(session, token)
        ledger = BudgetLedger(database)
        if not ledger.reserve(manifest['reel_id'], manifest['attempt_id'], 100):
            raise ValueError('Attempt already reserved; resubmission blocked')
        manifest['status'] = 'reserved'
        submitted = False
        try:
            manifest['quota_evidence'] = quota
            manifest['quota_claim'] = claim_quota(ledger, manifest, quota)
            save(directory, manifest)
            with MultipartUpload([(directory / 'presenter.png', 'image/png'), (directory / 'speech.wav', 'audio/wav')]) as body:
                paths = request_json(session, 'POST', HOST + '/gradio_api/upload', token, data=body,
                                     headers={'Content-Type': 'multipart/form-data; boundary=' + body.boundary})
            if not isinstance(paths, list) or len(paths) != 2 or any(not isinstance(path, str) or not path.startswith('/tmp/gradio/') or '..' in path.split('/') or any(c in path for c in '\r\n?#') for path in paths):
                raise ValueError('Unexpected private upload paths')
            validate_inputs(directory, manifest)
            validate_quota(quota)
            files = [{'path': path, 'meta': {'_type': 'gradio.FileData'}} for path in paths]
            manifest['status'] = 'submitting'
            save(directory, manifest)
            submitted = True
            result = request_json(session, 'POST', HOST + '/gradio_api/call/generate', token,
                                  json={'data': [*files, manifest['prompt'], *PARAMETERS.values()]})
            event_id = result.get('event_id')
            if not isinstance(event_id, str) or not re.fullmatch('[0-9a-f]{32}', event_id):
                raise ValueError('Unknown submission outcome; never resubmit')
            manifest.update(status='submitted', event_id=event_id)
            save(directory, manifest)
            return read_result(directory, token, session)
        except Exception as error:
            manifest.update(status='unknown' if submitted else 'failed_before_submission', error_class=type(error).__name__)
            save(directory, manifest)
            ledger.settle(manifest['reel_id'], manifest['attempt_id'], actual_cents=None if submitted else 0,
                          outcome='unknown' if submitted else 'failed')
            raise


def result_url(data):
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        raise ValueError('Unexpected video result')
    video = data[0].get('video', data[0])
    if not isinstance(video, dict):
        raise ValueError('Missing output file')
    url = video.get('url')
    if not url and isinstance(video.get('path'), str):
        url = HOST + '/gradio_api/file=' + quote(video['path'], safe='/')
    parsed = urlparse(url or '')
    if parsed.scheme != 'https' or parsed.netloc != urlparse(HOST).netloc or parsed.username or parsed.password or parsed.query or parsed.fragment or not re.fullmatch(r'/gradio_api/file=/tmp/gradio/[A-Za-z0-9_./-]+\.mp4', parsed.path) or '..' in parsed.path.split('/'):
        raise ValueError('Output must remain on the expected private media host')
    return url


def download_result(directory, manifest, url, token, session):
    target = directory / 'raw.mp4'
    if target.exists():
        if checksum(target, 50_000_000) != manifest.get('raw_sha256'):
            raise ValueError('Existing media cannot be overwritten')
    else:
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            staged = Path(temporary) / 'raw.mp4'
            with session.get(url, headers=auth(token), stream=True, allow_redirects=False, timeout=(15, 60)) as media:
                with staged.open('xb') as output:
                    for part in bounded_content(media, 50_000_000):
                        output.write(part)
            manifest['raw_sha256'] = checksum(staged, 50_000_000)
            save(directory, manifest)
            os.link(staged, target)
    manifest['status'] = 'downloaded'
    save(directory, manifest)
    return manifest


def read_result(directory, token, session=None):
    directory = Path(directory)
    manifest = load(directory)
    auth(token)
    if manifest.get('status') not in ('submitted', 'result_ready', 'unknown') or not re.fullmatch('[0-9a-f]{32}', manifest.get('event_id', '')):
        raise ValueError('A persisted provider event is required; do not create another job')
    owned = session is None
    session = session or requests.Session()
    session.trust_env = False
    deadline = time.monotonic() + 600
    buffer = b''
    event = ''
    try:
        if manifest.get('output_url'):
            url = result_url([{'url': manifest['output_url']}])
            return download_result(directory, manifest, url, token, session)
        with session.get(HOST + '/gradio_api/call/generate/' + manifest['event_id'], headers=auth(token),
                         stream=True, allow_redirects=False, timeout=(15, 60)) as response:
            for chunk in bounded_content(response, 1_000_000, deadline):
                if time.monotonic() > deadline:
                    raise TimeoutError('Result deadline reached; use result retrieval only')
                buffer += chunk
                if len(buffer) > 256_000:
                    raise ValueError('Oversized provider event')
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    if line.startswith(b'event:'):
                        event = line[6:].strip().decode()
                    elif line.startswith(b'data:') and event == 'error':
                        raise RuntimeError('Provider rejected the job; no automatic retry')
                    elif line.startswith(b'data:') and event == 'complete':
                        url = result_url(json.loads(line[5:].strip()))
                        manifest.update(status='result_ready', output_url=url)
                        save(directory, manifest)
                        return download_result(directory, manifest, url, token, session)
        raise ValueError('Provider stream ended without a result')
    except Exception as error:
        manifest.update(status='unknown', error_class=type(error).__name__)
        save(directory, manifest)
        raise
    finally:
        if owned:
            session.close()


def crop_geometry(width, height):
    if type(width) is not int or type(height) is not int or width < 18 or height < 32 or not 0.5 <= width / height <= 0.65:
        raise ValueError('A portrait presenter video is required')
    factor = min(width // 18, height // 32)
    cropped_width, cropped_height = 18 * factor, 32 * factor
    return cropped_width, cropped_height, (width - cropped_width) // 2, (height - cropped_height) // 2


def measure_video(path, expected_duration, *, normalized=False):
    import cv2

    capture = cv2.VideoCapture(str(path))
    try:
        width, height = (int(capture.get(prop)) for prop in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT))
        fps = capture.get(cv2.CAP_PROP_FPS)
        if (width, height) != ((468, 832) if normalized else (480, 832)) or not math.isfinite(fps) or abs(fps - 25) > 0.01:
            raise ValueError('Unexpected reviewed480p output dimensions or frame rate')
        frames = 0
        while True:
            ok, _ = capture.read()
            if not ok:
                break
            frames += 1
            if frames > math.ceil((expected_duration + 0.2) * fps):
                raise ValueError('Output exceeds the narration window')
    finally:
        capture.release()
    with tempfile.TemporaryDirectory() as temporary:
        decoded = Path(temporary) / 'audio.wav'
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-n', '-v', 'error', '-i', str(path),
                        '-map', '0:a:0', '-t', '6', '-ar', '16000', '-ac', '1', str(decoded)],
                       check=True, capture_output=True, timeout=30)
        with wave.open(str(decoded)) as audio:
            duration = audio.getnframes() / audio.getframerate()
            samples = array.array('h', audio.readframes(audio.getnframes()))
    rms = math.sqrt(sum(sample * sample for sample in samples) / max(1, len(samples)))
    if rms < 100 or abs(duration - expected_duration) > 0.1 or frames < 2 or frames / fps < expected_duration - 1 / fps or abs(frames / fps - expected_duration) > 0.2:
        raise ValueError('Missing, silent, truncated or misaligned narration/video')
    if normalized:
        validate_metrics(width, height, frames, fps, duration, expected_duration)
    return {'width': width, 'height': height, 'frames': frames, 'fps': fps,
            'audio_duration_seconds': duration, 'video_duration_seconds': frames / fps, 'narration_rms_pcm16': rms}


def normalize(directory):
    directory = Path(directory)
    manifest = load(directory)
    if manifest.get('status') != 'downloaded':
        raise ValueError('A downloaded, unprocessed attempt is required')
    duration = validate_inputs(directory, manifest)
    raw = directory / 'raw.mp4'
    if checksum(raw, 50_000_000) != manifest.get('raw_sha256'):
        raise ValueError('Provider output changed')
    before = measure_video(raw, duration)
    width, height, left, top = crop_geometry(before['width'], before['height'])
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        output = Path(temporary) / 'normalized.mp4'
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-n', '-v', 'error', '-i', str(raw),
                        '-i', str(directory / 'speech.wav'), '-map', '0:v:0', '-map', '1:a:0',
                        '-vf', f'crop={width}:{height}:{left}:{top},setsar=1', '-t', str(duration),
                        '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
                        '-b:a', '128k', '-movflags', '+faststart', str(output)],
                       check=True, capture_output=True, timeout=90)
        metrics = measure_video(output, duration, normalized=True)
        os.link(output, directory / 'normalized.mp4')
    manifest.update(status='media_validated', raw_media_validation=before, media_validation=metrics,
                    crop=[left, top, width, height], normalized_sha256=checksum(directory / 'normalized.mp4', 50_000_000))
    save(directory, manifest)
    return manifest


def attach_result(specification, directory):
    validated = build_manifest(specification)
    directory = Path(directory)
    attempt = load(directory)
    if attempt.get('status') != 'media_validated' or attempt.get('product_key') != validated['product_key'] or attempt.get('reel_id') != specification.get('reel_id'):
        raise ValueError('Validated media must belong to this exact pilot')
    duration = validate_inputs(directory, attempt)
    video = directory / 'normalized.mp4'
    if checksum(video, 50_000_000) != attempt['normalized_sha256']:
        raise ValueError('Normalized output changed')
    result = json.loads(json.dumps(specification))
    scene = next(scene for scene in result['scenes'] if scene['scene_id'] == attempt['scene_id'])
    asset = next(asset for asset in result['assets'] if asset['asset_id'] == scene['asset_id'])
    if scene['text'] != attempt['text'] or scene['asset_id'] != attempt['reference_asset_id'] or abs(scene['voice_duration_sec'] - duration) > 1 / 16000 or checksum(Path(asset['local_path']), LIMITS['presenter.png']) != attempt['files']['presenter.png'] or checksum(Path(scene['audio_path']), LIMITS['speech.wav']) != attempt['files']['speech.wav']:
        raise ValueError('Scene, voice or reference changed since generation')
    scene.update(generated_clip_path=str(video.resolve()), generated_clip_sha256=attempt['normalized_sha256'],
                 generation_attempt_id=attempt['attempt_id'], media_quality_status=attempt['quality_status'],
                 commercial_dependency_review=attempt['commercial_dependency_review'])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['prepare', 'submit', 'result', 'normalize', 'attach', 'configure-token', 'check-auth'])
    parser.add_argument('--directory', type=Path)
    parser.add_argument('--token-file', type=Path, help='Explicit local dotenv file; never auto-discovered or printed')
    parser.add_argument('--specification', type=Path)
    parser.add_argument('--scene-id')
    parser.add_argument('--quota', type=Path)
    parser.add_argument('--database', default='output/presenter_pilot_budget.sqlite')
    args = parser.parse_args()
    if args.operation not in ('configure-token', 'check-auth') and args.directory is None:
        parser.error('--directory is required for media operations')
    try:
        if args.operation == 'configure-token':
            if args.token_file is None:
                parser.error('configure-token requires explicit --token-file .env')
            result = configure_runtime_token(args.token_file)
        elif args.operation == 'check-auth':
            with closing(requests.Session()) as session:
                session.trust_env = False
                preflight(session, runtime_token(args.token_file))
            result = {'authentication': 'ok', 'space': SPACE, 'revision': REVISION, 'inference_started': False}
        elif args.operation in ('prepare', 'attach'):
            specification = json.loads(args.specification.read_text(encoding='utf-8'))
            result = prepare_scene(specification, args.scene_id, args.directory) if args.operation == 'prepare' else attach_result(specification, args.directory)
        elif args.operation == 'normalize':
            result = normalize(args.directory)
        elif args.operation == 'result':
            result = read_result(args.directory, runtime_token(args.token_file))
        else:
            result = submit(args.directory, args.database, runtime_token(args.token_file),
                            json.loads(args.quota.read_text(encoding='utf-8')))
    except LocalTokenError as error:
        parser.exit(2, 'Configuration blocked: ' + str(error) + '\n')
    except Exception as error:
        parser.exit(2, f'Pilot blocked ({type(error).__name__}); inspect local manifest status, never resubmit an uncertain job.\n')
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
