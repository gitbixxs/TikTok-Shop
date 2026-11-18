import getpass
import hashlib
import json
import math
import tempfile
import time
import unittest
import warnings
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image
import requests

from presenter_longcat_pilot import (
    HOST, PARAMETERS, REVISION, SPACE, MultipartUpload, attach_result, bounded_content, crop_geometry,
    configure_runtime_token, measure_video, normalize, prepare, prepare_scene, read_result,
    result_url, runtime_token, submit, validate_quota,
)
from presenter_pilot import BudgetLedger, build_manifest


def response(value):
    result = MagicMock()
    result.status_code = 200
    result.__enter__.return_value = result
    result.iter_content.return_value = [json.dumps(value).encode()]
    return result


class LongCatTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.image = self.root / 'source.png'
        self.audio = self.root / 'source.wav'
        Image.new('RGB', (432, 768), 'gray').save(self.image)
        with wave.open(str(self.audio), 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(b'\xe8\x03' * 32000)
        self.directory = self.root / 'attempt'
        self.database = self.root / 'budget.sqlite'
        self.ledger = BudgetLedger(self.database)
        self.ledger.create_reel('reel', overhead_cents=0)
        self.manifest = prepare(self.image, self.audio, self.directory,
                                reel_id='reel', scene_id='hook', text='Ein neutraler Test.')

    def tearDown(self):
        self.temp.cleanup()

    def quota(self):
        return {'current': 1200, 'overquotaUsed': 0, 'observed_at': time.time(), 'exclusive_use': True}

    def session(self):
        session = MagicMock()
        session.request.side_effect = [
            response({'id': SPACE, 'host': HOST, 'private': True, 'sha': REVISION,
                      'runtime': {'stage': 'RUNNING', 'hardware': {'current': 'zero-a10g'}}}),
            response({'named_endpoints': {'/generate': {'parameters': [
                {'parameter_name': name} for name in ('image_path', 'audio_path', 'prompt', *PARAMETERS)
            ]}}}),
            response(['/tmp/gradio/image/source.png', '/tmp/gradio/audio/source.wav']),
            response({'event_id': 'a' * 32}),
        ]
        return session

    def saved(self):
        return json.loads((self.directory / 'manifest.json').read_text())

    def test_preparation_measures_and_hashes_without_network(self):
        self.assertEqual(self.manifest['audio_duration_seconds'], 2)
        self.assertEqual(self.manifest['status'], 'prepared')
        self.assertEqual(len(self.manifest['files']), 2)
        self.assertFalse(self.manifest['production_approved'])
        with self.assertRaises(FileExistsError):
            prepare(self.image, self.audio, self.directory, reel_id='reel', scene_id='hook', text='Test')

    def test_audio_over_fixed_window_is_blocked(self):
        with wave.open(str(self.audio), 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(b'\xe8\x03' * 80000)
        with self.assertRaises(ValueError):
            prepare(self.image, self.audio, self.root / 'too_long', reel_id='reel', scene_id='cta', text='Test')

    def test_quota_must_be_fresh_sufficient_and_exclusive(self):
        self.assertEqual(validate_quota(self.quota()), 1200)
        for change in ({'current': 599}, {'overquotaUsed': 1}, {'observed_at': time.time() - 121},
                       {'observed_at': time.time() + 10}, {'exclusive_use': False}, {'current': math.nan}):
            with self.assertRaises(ValueError):
                validate_quota({**self.quota(), **change})

    def test_changed_inputs_block_before_network(self):
        (self.directory / 'speech.wav').write_bytes(b'changed')
        with patch('presenter_longcat_pilot.requests.Session') as factory:
            with self.assertRaises(ValueError):
                submit(self.directory, self.database, 'test-token', self.quota())
            factory.assert_not_called()

    def test_stale_quota_and_missing_auth_block_before_network(self):
        with patch('presenter_longcat_pilot.requests.Session') as factory:
            for token, quota in [('', self.quota()), ('test-token', {})]:
                with self.assertRaises(ValueError):
                    submit(self.directory, self.database, token, quota)
            factory.assert_not_called()

    def test_wrong_runtime_or_revision_blocks_upload(self):
        for field, value in [('sha', 'unreviewed'), ('private', False), ('host', 'https://other.example')]:
            session = self.session()
            session.request.side_effect = [response({
                'id': SPACE, 'host': HOST, 'private': True, 'sha': REVISION,
                'runtime': {'stage': 'RUNNING', 'hardware': {'current': 'zero-a10g'}}, field: value,
            })]
            with patch('presenter_longcat_pilot.requests.Session', return_value=session):
                with self.assertRaises(ValueError):
                    submit(self.directory, self.database, 'test-token', self.quota())
            self.assertEqual(session.request.call_count, 1)
            self.assertEqual(self.ledger.summary('reel')['remaining_cents'], 100)

    def test_unknown_submission_blocks_retry_and_keeps_budget(self):
        session = self.session()
        session.request.side_effect = list(session.request.side_effect)[:3] + [TimeoutError('do not log token')]
        with patch('presenter_longcat_pilot.requests.Session', return_value=session):
            with self.assertRaises(TimeoutError):
                submit(self.directory, self.database, 'test-token', self.quota())
        self.assertEqual(self.saved()['status'], 'unknown')
        self.assertEqual(self.ledger.summary('reel')['remaining_cents'], 0)
        self.assertNotIn('test-token', (self.directory / 'manifest.json').read_text())
        with patch('presenter_longcat_pilot.requests.Session') as factory:
            with self.assertRaises(ValueError):
                submit(self.directory, self.database, 'test-token', self.quota())
            factory.assert_not_called()

    def test_upload_failure_does_not_submit_generation(self):
        session = self.session()
        session.request.side_effect = list(session.request.side_effect)[:2] + [TimeoutError()]
        with patch('presenter_longcat_pilot.requests.Session', return_value=session):
            with self.assertRaises(TimeoutError):
                submit(self.directory, self.database, 'test-token', self.quota())
        self.assertEqual(self.saved()['status'], 'failed_before_submission')
        self.assertEqual(self.ledger.summary('reel')['remaining_cents'], 100)
        self.assertFalse(any('/call/generate' in call.args[1] for call in session.request.call_args_list))

    def test_successful_submit_has_exact_order_and_no_implicit_acceptance(self):
        session = self.session()
        with patch('presenter_longcat_pilot.requests.Session', return_value=session), \
             patch('presenter_longcat_pilot.read_result', side_effect=lambda directory, token, session: self.saved()):
            result = submit(self.directory, self.database, 'test-token', self.quota())
        data = session.request.call_args.kwargs['json']['data']
        self.assertEqual(data[0]['path'], '/tmp/gradio/image/source.png')
        self.assertEqual(data[1]['path'], '/tmp/gradio/audio/source.wav')
        self.assertEqual(data[3:], ['480p', 72, 'Clean speech (fast)', 'Exact 8-step'])
        self.assertEqual(result['status'], 'submitted')
        self.assertEqual(self.ledger.summary('reel')['remaining_cents'], 0)
        self.assertTrue(all(call.kwargs['allow_redirects'] is False for call in session.request.call_args_list))

    def test_multipart_is_sized_and_streamed(self):
        with MultipartUpload([(self.image, 'image/png'), (self.audio, 'audio/wav')]) as upload:
            chunks = list(upload)
            self.assertEqual(sum(map(len, chunks)), len(upload))
            self.assertLessEqual(max(map(len, chunks)), 65536)
            self.assertEqual(b''.join(chunks).count(b'name="files"'), 2)

    def test_crop_preserves_native_scale_and_exact_even_916(self):
        self.assertEqual(crop_geometry(480, 832), (468, 832, 6, 0))
        self.assertEqual(crop_geometry(432, 768), (432, 768, 0, 0))
        for dimensions in [(0, 0), (10, 10), (832, 480)]:
            with self.assertRaises(ValueError):
                crop_geometry(*dimensions)

    def test_normalization_uses_prepared_narration_without_stretching(self):
        manifest = self.saved()
        manifest.update(status='downloaded', raw_sha256=hashlib.sha256(b'offline').hexdigest())
        (self.directory / 'manifest.json').write_text(json.dumps(manifest))
        (self.directory / 'raw.mp4').write_bytes(b'offline')
        def render(command, **kwargs):
            Path(command[-1]).write_bytes(b'normalized')
        metrics = {'width': 480, 'height': 832, 'frames': 51, 'fps': 25, 'audio_duration_seconds': 2}
        with patch('presenter_longcat_pilot.measure_video', side_effect=[metrics, {**metrics, 'width': 468}]), \
             patch('presenter_longcat_pilot.subprocess.run', side_effect=render) as run:
            result = normalize(self.directory)
        command = run.call_args.args[0]
        self.assertIn('crop=468:832:6:0,setsar=1', command)
        self.assertNotIn('scale=', ' '.join(command))
        self.assertIn(str(self.directory / 'speech.wav'), command)
        self.assertEqual(result['status'], 'media_validated')
        self.assertFalse(result['production_approved'])

    def test_requests_preserves_streaming_body_and_content_length(self):
        with MultipartUpload([(self.image, 'image/png')]) as upload:
            prepared = requests.Request('POST', HOST + '/gradio_api/upload', data=upload).prepare()
            self.assertIs(prepared.body, upload)
            self.assertEqual(int(prepared.headers['Content-Length']), len(upload))
            self.assertNotIn('Transfer-Encoding', prepared.headers)

    def test_metadata_response_size_and_redirects_are_bounded(self):
        for status, chunks in [(302, []), (200, [b'x' * 65536, b'y'])]:
            item = response({})
            item.status_code = status
            item.iter_content.return_value = chunks
            with self.assertRaises(ValueError):
                list(bounded_content(item, 65536))

    def test_result_urls_reject_other_hosts_credentials_queries_and_traversal(self):
        valid = HOST + '/gradio_api/file=/tmp/gradio/abc/longcat.mp4'
        self.assertEqual(result_url([{'video': {'url': valid}}]), valid)
        for url in [valid.replace('https:', 'http:'), valid.replace(HOST, 'https://other.example'),
                    valid.replace('https://', 'https://user:password@'), valid + '?token=secret',
                    HOST + '/gradio_api/file=/tmp/gradio/../../outside.mp4',
                    HOST + '/gradio_api/file=/tmp/gradio/%2e%2e/outside.mp4']:
            with self.assertRaises(ValueError):
                result_url([{'video': {'url': url}}])

    def submitted(self):
        manifest = self.saved()
        manifest.update(status='submitted', event_id='a' * 32)
        (self.directory / 'manifest.json').write_text(json.dumps(manifest))

    def result_response(self, url=None):
        item = response({})
        value = [{'video': {'url': url or HOST + '/gradio_api/file=/tmp/gradio/abc/result.mp4'}}]
        item.iter_content.return_value = [('event: complete\ndata: ' + json.dumps(value) + '\n\n').encode()]
        return item

    def test_result_retrieval_is_get_only_and_does_not_release_budget(self):
        self.submitted()
        self.ledger.reserve('reel', self.manifest['attempt_id'], 100)
        session = MagicMock()
        media = response({})
        media.iter_content.return_value = [b'offline-mp4']
        session.get.side_effect = [self.result_response(), media]
        result = read_result(self.directory, 'test-token', session)
        self.assertEqual(result['status'], 'downloaded')
        self.assertEqual((self.directory / 'raw.mp4').read_bytes(), b'offline-mp4')
        session.post.assert_not_called()
        session.request.assert_not_called()
        self.assertEqual(self.ledger.summary('reel')['remaining_cents'], 0)
        self.assertTrue(all(call.kwargs['allow_redirects'] is False for call in session.get.call_args_list))

    def test_foreign_result_never_receives_private_authorization(self):
        self.submitted()
        session = MagicMock()
        session.get.return_value = self.result_response('https://other.example/result.mp4')
        with self.assertRaises(ValueError):
            read_result(self.directory, 'test-token', session)
        self.assertEqual(session.get.call_count, 1)
        self.assertEqual(self.saved()['status'], 'unknown')

    def test_result_download_redirect_fails_without_committing_media(self):
        self.submitted()
        session = MagicMock()
        redirect = response({})
        redirect.status_code = 302
        session.get.side_effect = [self.result_response(), redirect]
        with self.assertRaises(ValueError):
            read_result(self.directory, 'test-token', session)
        self.assertFalse((self.directory / 'raw.mp4').exists())
        self.assertEqual(self.saved()['status'], 'unknown')

    def test_oversized_sse_line_is_rejected_without_download(self):
        self.submitted()
        session = MagicMock()
        item = response({})
        item.iter_content.return_value = [b'x' * 65536] * 5
        session.get.return_value = item
        with self.assertRaises(ValueError):
            read_result(self.directory, 'test-token', session)
        self.assertEqual(session.get.call_count, 1)

    def test_quota_snapshot_cannot_authorize_another_attempt(self):
        quota = self.quota()
        session = self.session()
        with patch('presenter_longcat_pilot.requests.Session', return_value=session), \
             patch('presenter_longcat_pilot.read_result', return_value={}):
            submit(self.directory, self.database, 'test-token', quota)
        self.ledger.settle('reel', self.manifest['attempt_id'], actual_cents=0, outcome='accepted')
        other = self.root / 'other'
        prepare(self.image, self.audio, other, reel_id='reel', scene_id='cta', text='Test.')
        session = self.session()
        with patch('presenter_longcat_pilot.requests.Session', return_value=session):
            with self.assertRaises(ValueError):
                submit(other, self.database, 'test-token', quota)
        self.assertEqual(session.request.call_count, 2)
        self.assertEqual(self.ledger.summary('reel')['remaining_cents'], 100)

    def specification(self):
        scenes = [
            {'scene_id': 'hook', 'role': 'hook', 'visual': 'presenter', 'asset_id': 'presenter', 'text': 'Ein neutraler Test.', 'voice_duration_sec': 2, 'generation_provider': 'longcat15', 'audio_path': str(self.audio)},
            {'scene_id': 'detail', 'role': 'body', 'visual': 'product', 'asset_id': 'product', 'text': 'Nur eine Offline-Fixture.', 'voice_duration_sec': 25},
            {'scene_id': 'cta', 'role': 'cta', 'visual': 'presenter', 'asset_id': 'presenter', 'text': 'Noch ein Test.', 'voice_duration_sec': 2, 'generation_provider': 'longcat15', 'audio_path': str(self.audio)},
        ]
        for scene in scenes:
            scene['claim_sources'] = ['offline fixture, not real product evidence']
            if scene.get('generation_provider') == 'longcat15':
                scene['longcat_prompt'] = 'Reviewed offline fixture prompt for this scene.'
        return {'reel_id': 'reel', 'product_key': 'fixture-sku', 'scenes': scenes, 'assets': [
            {'asset_id': 'presenter', 'kind': 'presenter', 'source': 'offline fixture', 'local_path': str(self.image), 'identity_status': 'fictional', 'rights_status': 'owned', 'rights_evidence': 'offline fixture', 'quality_status': 'accepted'},
            {'asset_id': 'product', 'kind': 'product', 'product_key': 'fixture-sku', 'source': 'offline fixture', 'rights_status': 'owned', 'rights_evidence': 'offline fixture', 'quality_status': 'accepted'},
        ]}

    def test_prepare_scene_binds_to_reviewed_product_timeline_and_voice(self):
        result = prepare_scene(self.specification(), 'hook', self.root / 'bound')
        self.assertEqual(result['product_key'], 'fixture-sku')
        self.assertEqual(result['reference_asset_id'], 'presenter')
        self.assertEqual(result['audio_duration_seconds'], 2)

    def test_unlicensed_assets_and_mismatching_audio_block_preparation(self):
        for field, value in [('rights_status', 'unknown'), ('product_key', 'other')]:
            spec = self.specification()
            spec['assets'][1][field] = value
            with self.assertRaises(ValueError):
                prepare_scene(spec, 'hook', self.root / 'blocked')
            self.assertFalse((self.root / 'blocked').exists())
        spec = self.specification()
        spec['scenes'][0]['voice_duration_sec'] = 2.2
        with self.assertRaises(ValueError):
            prepare_scene(spec, 'hook', self.root / 'mismatch')
        self.assertFalse((self.root / 'mismatch').exists())

    def test_too_long_longcat_scene_and_unreviewed_output_block_manifest(self):
        spec = self.specification()
        spec['scenes'][0]['voice_duration_sec'] = 4.9
        with self.assertRaises(ValueError):
            build_manifest(spec)
        spec = self.specification()
        spec['scenes'][0].update(generated_clip_path='fixture.mp4', media_quality_status='pending', commercial_dependency_review='pending')
        with self.assertRaises(ValueError):
            build_manifest(spec)

    def test_attached_media_stays_pending_until_visual_and_commercial_review(self):
        spec = self.specification()
        directory = self.root / 'bound'
        manifest = prepare_scene(spec, 'hook', directory)
        (directory / 'normalized.mp4').write_bytes(b'offline-video-fixture')
        manifest.update(status='media_validated', normalized_sha256=hashlib.sha256(b'offline-video-fixture').hexdigest())
        (directory / 'manifest.json').write_text(json.dumps(manifest))
        attached = attach_result(spec, directory)
        self.assertIn('generated_clip_path', attached['scenes'][0])
        with self.assertRaises(ValueError):
            build_manifest(attached)
        attached['scenes'][0]['media_quality_status'] = 'accepted'
        with self.assertRaises(ValueError):
            build_manifest(attached)
        attached['scenes'][0]['commercial_dependency_review'] = 'accepted'
        self.assertTrue(build_manifest(attached)['draft_only'])
        spec['scenes'][0]['voice_duration_sec'] = 2.1
        with self.assertRaises(ValueError):
            attach_result(spec, directory)

    def test_completed_result_can_resume_download_without_replaying_sse(self):
        self.submitted()
        first = MagicMock()
        first.get.side_effect = [self.result_response(), TimeoutError()]
        with self.assertRaises(TimeoutError):
            read_result(self.directory, 'test-token', first)
        self.assertIn('output_url', self.saved())
        second = MagicMock()
        media = response({})
        media.iter_content.return_value = [b'recovered-video']
        second.get.return_value = media
        result = read_result(self.directory, 'test-token', second)
        self.assertEqual(result['status'], 'downloaded')
        self.assertEqual(second.get.call_count, 1)
        self.assertIn('/gradio_api/file=', second.get.call_args.args[0])
        second.post.assert_not_called()

    def test_resuming_result_never_overwrites_existing_media(self):
        self.submitted()
        (self.directory / 'raw.mp4').write_bytes(b'existing-file')
        session = MagicMock()
        session.get.return_value = self.result_response()
        with self.assertRaises(ValueError):
            read_result(self.directory, 'test-token', session)
        self.assertEqual((self.directory / 'raw.mp4').read_bytes(), b'existing-file')
        self.assertEqual(session.get.call_count, 1)

    def test_video_must_cover_the_whole_narration(self):
        capture = MagicMock()
        capture.get.side_effect = [480, 832, 25]
        capture.read.side_effect = [(True, None)] * 48 + [(False, None)]
        def decode(command, **kwargs):
            Path(command[-1]).write_bytes(self.audio.read_bytes())
        with patch('cv2.VideoCapture', return_value=capture), \
             patch('presenter_longcat_pilot.subprocess.run', side_effect=decode):
            with self.assertRaises(ValueError):
                measure_video(self.root / 'fixture.mp4', 2)

    def test_token_file_is_explicit_and_only_reads_named_key(self):
        token = 'hf_' + 'a' * 34
        path = self.root / '.env'
        path.write_text('OTHER=value\nHF_CREATIVE_TOKEN="' + token + '"\n', encoding='utf-8')
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ValueError):
                runtime_token()
            self.assertEqual(runtime_token(path), token)

    def test_ambiguous_invalid_or_oversized_token_files_are_rejected(self):
        token = 'hf_' + 'a' * 34
        path = self.root / '.env'
        for content in ['HF_CREATIVE_TOKEN=' + token + '\nHF_CREATIVE_TOKEN=' + token,
                        'HF_CREATIVE_TOKEN=invalid-value', 'x' * 65537]:
            path.write_text(content, encoding='utf-8')
            with self.assertRaises(ValueError):
                runtime_token(path)

    def test_secure_setup_refuses_agent_or_noninteractive_input(self):
        path = self.root / '.env'
        with patch('presenter_longcat_pilot.sys.stdin.isatty', return_value=False), \
             patch('presenter_longcat_pilot.getpass.getpass') as prompt:
            with self.assertRaises(ValueError):
                configure_runtime_token(path)
            prompt.assert_not_called()
        self.assertFalse(path.exists())

    def test_secure_setup_requires_ignored_repository_env_file(self):
        path = self.root / '.env'
        with patch('presenter_longcat_pilot.PROJECT_ROOT', self.root), \
             patch('presenter_longcat_pilot.sys.stdin.isatty', return_value=True), \
             patch('presenter_longcat_pilot.subprocess.run', return_value=MagicMock(returncode=1)), \
             patch('presenter_longcat_pilot.getpass.getpass') as prompt:
            with self.assertRaises(ValueError):
                configure_runtime_token(path)
            prompt.assert_not_called()
        self.assertFalse(path.exists())

    def test_secure_setup_preserves_other_values_and_never_returns_token(self):
        token = 'hf_' + 'a' * 34
        path = self.root / '.env'
        previous = 'OTHER=value\n'
        path.write_text(previous, encoding='utf-8')
        with patch('presenter_longcat_pilot.PROJECT_ROOT', self.root), \
             patch('presenter_longcat_pilot.sys.stdin.isatty', return_value=True), \
             patch('presenter_longcat_pilot.subprocess.run', return_value=MagicMock(returncode=0)), \
             patch('presenter_longcat_pilot.getpass.getpass', return_value=token):
            result = configure_runtime_token(path)
        self.assertTrue(path.read_text().startswith(previous))
        self.assertEqual(runtime_token(path), token)
        self.assertNotIn(token, json.dumps(result))
        self.assertFalse(result['inference_started'])

    def test_secure_setup_does_not_overwrite_existing_token(self):
        token = 'hf_' + 'a' * 34
        path = self.root / '.env'
        content = 'HF_CREATIVE_TOKEN=' + token + '\n'
        path.write_text(content, encoding='utf-8')
        with patch('presenter_longcat_pilot.PROJECT_ROOT', self.root), \
             patch('presenter_longcat_pilot.sys.stdin.isatty', return_value=True), \
             patch('presenter_longcat_pilot.subprocess.run', return_value=MagicMock(returncode=0)), \
             patch('presenter_longcat_pilot.getpass.getpass') as prompt:
            result = configure_runtime_token(path)
            prompt.assert_not_called()
        self.assertTrue(result['already_present'])
        self.assertEqual(path.read_text(), content)

    def test_secure_setup_aborts_if_hidden_input_is_unavailable(self):
        path = self.root / '.env'
        def unavailable(prompt):
            warnings.warn('No echo control', getpass.GetPassWarning)
        with patch('presenter_longcat_pilot.PROJECT_ROOT', self.root), \
             patch('presenter_longcat_pilot.sys.stdin.isatty', return_value=True), \
             patch('presenter_longcat_pilot.subprocess.run', return_value=MagicMock(returncode=0)), \
             patch('presenter_longcat_pilot.getpass.getpass', side_effect=unavailable):
            with self.assertRaises(getpass.GetPassWarning):
                configure_runtime_token(path)
        self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
