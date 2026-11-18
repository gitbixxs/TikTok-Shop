import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw


class FixedResolutionParser:
    def __call__(self, image, mode='jaw'):
        mask = Image.new('L', (512, 512), 0)
        ImageDraw.Draw(mask).rectangle((220, 300, 300, 400), fill=255)
        return mask


def load_blending():
    parser = types.ModuleType('musetalk.utils.face_parsing')
    parser.FaceParsing = FixedResolutionParser
    root = Path(__file__).resolve().parents[1]
    path = root / 'hf_spaces/tiktok_lipsync_worker/musetalk/utils/blending.py'
    spec = importlib.util.spec_from_file_location('musetalk.utils.blending', path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'musetalk.utils.face_parsing': parser}):
        spec.loader.exec_module(module)
    return module


class BlendingTests(unittest.TestCase):
    def setUp(self):
        self.blending = load_blending()
        self.image = np.zeros((768, 432, 3), dtype=np.uint8)
        self.face = np.full((319, 200, 3), 255, dtype=np.uint8)
        self.box = (132, 195, 332, 514)

    def test_parser_mask_is_rescaled_before_coordinate_crop(self):
        result = self.blending.get_image(self.image, self.face, self.box, fp=FixedResolutionParser())
        self.assertEqual(result[410, 232].tolist(), [255, 255, 255])

    def test_upper_face_and_body_are_preserved(self):
        result = self.blending.get_image(self.image, self.face, self.box, fp=FixedResolutionParser())
        self.assertEqual(result.shape, self.image.shape)
        self.assertEqual(result.dtype, np.uint8)
        self.assertFalse(result[220, 232].any())
        self.assertFalse(result[600, 232].any())
        self.assertFalse(result[410, 20].any())

    def test_default_parser_has_same_alignment(self):
        explicit = self.blending.get_image(self.image, self.face, self.box, fp=FixedResolutionParser())
        implicit = self.blending.get_image(self.image, self.face, self.box)
        np.testing.assert_array_equal(explicit, implicit)

    def test_parser_without_mode_remains_supported(self):
        class LegacyParser:
            def __call__(self, image):
                return FixedResolutionParser()(image)
        result = self.blending.get_image(self.image, self.face, self.box, fp=LegacyParser())
        self.assertEqual(result[410, 232].tolist(), [255, 255, 255])


if __name__ == '__main__':
    unittest.main()
