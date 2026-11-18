import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

from diagnose_presenter_alignment import alignment_geometry
from presenter_lipsync_pilot import ATTEMPT, REEL, download, gpu_seconds, prepare, request_profile, safe_url, stage_existing_test_inputs, submit, validate_metrics
from presenter_pilot import BudgetLedger


class LipSyncTests(unittest.TestCase):
    def test_staging_uploads_only_existing_test_files_without_inference(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            files = {'speech.wav': b'offline-audio', 'presenter_crop.png': b'offline-image'}
            for name, content in files.items():
                (directory / name).write_bytes(content)
            (directory / 'manifest.json').write_text(json.dumps({'files': {
                name: hashlib.sha256(content).hexdigest() for name, content in files.items()
            }}))
            with patch('presenter_lipsync_pilot.requests.Session') as factory:
                session = factory.return_value
                session.post.return_value.json.return_value = ['/tmp/gradio/a/speech.wav', '/tmp/gradio/b/presenter_crop.png']
                result = stage_existing_test_inputs(directory)
                session.post.assert_called_once()
                self.assertTrue(session.post.call_args.args[0].endswith('/gradio_api/upload'))
                self.assertFalse(session.trust_env)
                self.assertNotIn('headers', session.post.call_args.kwargs)
            self.assertIn('speech.wav', result['audio_url'])
            self.assertIn('upload only', result['purpose'])

    def test_alignment_midline_moves_to_target(self):
        geometry = alignment_geometry((100, 100, 160, 200), 170, 210, 768)
        self.assertLess(geometry['bbox_shift_candidate'], 0)
        self.assertLessEqual(abs(geometry['adjusted_proxy_midline'] - geometry['nose_bridge_target_approximation']), 0.5)
        self.assertIn('proxy', geometry['method_limit'])

    def test_invalid_landmarks_are_rejected(self):
        for nose in (100, 160, 400, float('nan')):
            with self.assertRaises(ValueError):
                alignment_geometry((100, 100, 160, 200), 170, nose, 768)

    def test_attempt_ids_bind_to_reviewed_alignment(self):
        self.assertEqual(request_profile({'reel_id': REEL, 'attempt_id': ATTEMPT}), (ATTEMPT, 0))
        profile = {'reel_id': REEL, 'attempt_id': 'hf_musetalk15_jonas_alignment_v1', 'bbox_shift': -83}
        self.assertEqual(request_profile(profile)[1], -83)
        for shift in (0, 83, True, -84):
            with self.assertRaises(ValueError):
                request_profile({**profile, 'bbox_shift': shift})
        with self.assertRaises(ValueError):
            request_profile({**profile, 'attempt_id': 'unbounded-retry'})

    def test_bounded_duration(self):
        self.assertEqual(gpu_seconds(3), 99)
        self.assertLessEqual(gpu_seconds(4), 120)
        for duration in (0, -1, 4.01, float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                gpu_seconds(duration)

    def test_complete_measured_media(self):
        self.assertEqual(validate_metrics(432, 768, 68, 25, 2.74, 2.736), 2.72)

    def test_bad_or_truncated_media_is_rejected(self):
        for metrics in ((432, 768, 1, 25, 2.74, 2.736), (432, 768, 68, 0, 2.74, 2.736),
                        (768, 432, 68, 25, 2.74, 2.736), (432, 768, 30, 25, 2.74, 2.736),
                        (432, 768, 68, 25, 0, 2.736), (432, 768, 68, 25, float('nan'), 2.736)):
            with self.assertRaises(ValueError):
                validate_metrics(*metrics)

    def test_media_hosts_are_restricted(self):
        for url in ('http://example.org/a', 'https://other.org/a', 'https://user:secret@example.org/a', 'file:///tmp/a'):
            with self.assertRaises(ValueError):
                safe_url(url, 'example.org')
        self.assertEqual(safe_url('https://example.org/a', 'example.org'), 'https://example.org/a')

    def test_download_rejects_redirects(self):
        session = MagicMock()
        session.get.return_value.__enter__.return_value.status_code = 302
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                download(session, 'https://example.org/a', Path(temp) / 'a', 'example.org', 100)
        self.assertFalse(session.get.call_args.kwargs['allow_redirects'])

    def test_preparation_measures_audio_and_crops_without_upscale(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'source.png'
            Image.new('RGB', (576, 1024)).save(source)
            directory = Path(temp) / 'assets'
            def fake_download(session, url, path, host, limit):
                path.write_bytes(b'offline-mp3-fixture')
            def fake_convert(command, **kwargs):
                with wave.open(command[-1], 'wb') as audio:
                    audio.setnchannels(1)
                    audio.setsampwidth(2)
                    audio.setframerate(16000)
                    audio.writeframes(b'\0\0' * 48000)
            with patch('presenter_lipsync_pilot.requests.Session') as session, patch('presenter_lipsync_pilot.download', side_effect=fake_download), patch('presenter_lipsync_pilot.subprocess.run', side_effect=fake_convert):
                session.return_value.post.return_value.json.return_value = {'voice_url': 'https://ffmpeg.mafrapi.eu/temp/test.mp3'}
                result = prepare(source, directory)
            self.assertEqual(result['audio_duration_seconds'], 3)
            self.assertEqual(result['status'], 'prepared')
            self.assertFalse(result['production_approved'])
            with Image.open(directory / 'presenter_crop.png') as crop:
                self.assertEqual(crop.size, (432, 768))
            self.assertEqual(len(result['files']), 4)

    def test_nonprepared_attempt_cannot_be_submitted(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / 'manifest.json').write_text(json.dumps({'status': 'submitted'}))
            with patch('presenter_lipsync_pilot.requests.Session') as session:
                with self.assertRaises(ValueError):
                    submit(directory, str(directory / 'budget.sqlite'))
                session.assert_not_called()

    def test_edited_assets_block_before_network(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / 'speech.wav').write_bytes(b'changed')
            (directory / 'manifest.json').write_text(json.dumps({
                'status': 'prepared', 'reel_id': REEL, 'attempt_id': ATTEMPT,
                'audio_duration_seconds': 3, 'files': {'speech.wav': 'incorrect-hash'},
            }))
            with patch('presenter_lipsync_pilot.requests.Session') as session:
                with self.assertRaises(ValueError):
                    submit(directory, str(directory / 'budget.sqlite'))
                session.assert_not_called()

    def test_unknown_attempt_keeps_budget_reserved(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = BudgetLedger(Path(temp) / 'budget.sqlite')
            ledger.create_reel(REEL, overhead_cents=0)
            self.assertTrue(ledger.reserve(REEL, ATTEMPT, 100))
            ledger.settle(REEL, ATTEMPT, actual_cents=None, outcome='unknown')
            self.assertEqual(ledger.summary(REEL)['remaining_cents'], 0)
            self.assertFalse(ledger.reserve(REEL, ATTEMPT, 100))


if __name__ == '__main__':
    unittest.main()
