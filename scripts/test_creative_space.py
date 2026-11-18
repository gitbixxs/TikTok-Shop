import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / 'hf_spaces' / 'tiktok_creative_worker' / 'app.py'


class SpaceTests(unittest.TestCase):
    def load_app(self, enabled='0', zero_gpu=''):
        gradio = types.ModuleType('gradio')
        gradio.Error = ValueError
        specification = importlib.util.spec_from_file_location('creative_space_test', APP)
        module = importlib.util.module_from_spec(specification)
        with patch.dict(sys.modules, {'gradio': gradio}), patch.dict(os.environ, {
            'ENABLE_GENERATION': enabled, 'SPACES_ZERO_GPU': zero_gpu,
            'HF_MODEL_TOKEN': '', 'HF_CREATIVE_TOKEN': 'not-a-real-token',
        }):
            specification.loader.exec_module(module)
        return module

    def test_bootstrap_has_no_inference_or_secret_output(self):
        app = self.load_app()
        result = app.health()
        self.assertFalse(result['generation_enabled'])
        self.assertFalse(result['model_loaded'])
        self.assertEqual(result['capabilities'], ['health'])
        self.assertNotIn('not-a-real-token', str(result))
        self.assertFalse(result['product_edit'])
        self.assertFalse(result['video_generation'])
        self.assertFalse(result['lip_sync'])

    def test_generation_is_blocked_by_default(self):
        with self.assertRaisesRegex(ValueError, 'Generation is disabled'):
            self.load_app().generate_presenter('jonas', 'front', 72)

    def test_cpu_and_paid_dedicated_hardware_cannot_enable_inference(self):
        with self.assertRaisesRegex(RuntimeError, 'requires ZeroGPU'):
            self.load_app(enabled='1')

    def test_missing_model_access_blocks_download(self):
        with self.assertRaisesRegex(RuntimeError, 'HF_MODEL_TOKEN'):
            self.load_app(enabled='1', zero_gpu='true')

    def test_request_limits(self):
        app = self.load_app()
        self.assertEqual(app.validate_request('jonas', 'front', 72), 72)
        for seed in [-1, 1.5, 2147483648, float('nan'), float('inf'), True, '72']:
            with self.assertRaises(ValueError):
                app.validate_request('jonas', 'front', seed)
        with self.assertRaises(ValueError):
            app.validate_request('unknown', 'front', 72)
        with self.assertRaises(ValueError):
            app.validate_request('jonas', 'arbitrary-prompt', 72)

    def test_manifest_and_dependencies_are_pinned(self):
        directory = APP.parent
        metadata = (directory / 'README.md').read_text(encoding='utf-8')
        self.assertIn('sdk: gradio', metadata)
        description = next(line.split(':', 1)[1].strip() for line in metadata.splitlines() if line.startswith('short_description:'))
        self.assertLessEqual(len(description), 60)
        self.assertIn('python_version: "3.12.12"', metadata)
        requirements = (directory / 'requirements.txt').read_text(encoding='utf-8').splitlines()
        self.assertTrue(all('==' in requirement for requirement in requirements))
        self.assertIn('gradio==6.31.0', requirements)
        pillow = next(line.split('==')[1] for line in requirements if line.lower().startswith('pillow=='))
        self.assertLess(int(pillow.split('.')[0]), 13)


if __name__ == '__main__':
    unittest.main()
