"""An unknown OCR API response must never masquerade as a clean page."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

from privacyguard.ocr.rapidocr import RapidOCREngine
from privacyguard.utils.exceptions import OCRInspectionError


class OcrOutputGuardTests(unittest.TestCase):
    def recognize(self, output):
        engine = RapidOCREngine()
        engine._engine = Mock(return_value=output)
        with patch.object(RapidOCREngine, '_shared_init_failed', False):
            return engine.recognize(np.zeros((20,100,3),dtype=np.uint8))

    def test_canonical_blank_result_is_empty(self):
        self.assertEqual(self.recognize(SimpleNamespace(boxes=None,txts=None)), [])
        self.assertEqual(self.recognize(([], .1)), [])

    def test_unknown_response_raises_inspection_error(self):
        with self.assertRaises(OCRInspectionError):
            self.recognize({'changed_api':'PRIVATE_INPUT'})

    def test_partial_response_raises_instead_of_dropping_text(self):
        with self.assertRaises(OCRInspectionError):
            self.recognize(SimpleNamespace(boxes=[],txts=['SECRET']))
