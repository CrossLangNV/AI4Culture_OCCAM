import os
import os.path
import tempfile
import unittest
import warnings

import pdf2image

from ocr.connector import LocalOcrConnector

FILENAME_IMAGE = "test_image.jpg"
FILENAME_IMAGE = os.path.join(os.path.dirname(__file__), FILENAME_IMAGE)
FILENAME_PDF = os.path.join(os.path.dirname(__file__), "../test_data", "example_scanned.pdf")

if not os.path.exists(FILENAME_IMAGE):
    warnings.warn(f"File {FILENAME_IMAGE} does not exist for testing OCR")


class TestLocalOcrConnector(unittest.TestCase):
    """
    Integration tests of OCR API connector
    """

    def setUp(self) -> None:
        self.connector = LocalOcrConnector()

    def test_ocr_response(self):
        """
        Test that a user can OCR an image
        """

        with open(FILENAME_IMAGE, "rb") as file:
            data = self.connector.ocr_image(file)

        text = data.get("text")

        with self.subTest("Non-empty response"):
            self.assertTrue(text)

        with self.subTest("Correct OCR output"):
            self.assertIn("transformation en société anonyme", text)

        xml = data.get("xml")

        with self.subTest("PageXML output"):
            self.assertTrue(xml, "No output")
            self.assertIn(
                "http://schema.primaresearch.org/PAGE",
                xml,
                "Should contain PAGE XML namespace",
            )

    def test_from_PIL(self):
        """
        Test that a user can OCR an image from a PIL image
        """

        with open(FILENAME_PDF, "rb") as _file:
            images = pdf2image.convert_from_bytes(_file.read(), fmt="png", dpi=300)

        image = images[0]
        with tempfile.TemporaryDirectory() as tempdir:
            filename = os.path.join(tempdir, "test.png")
            image.save(filename)

            with open(filename, "rb") as file:
                data = self.connector.ocr_image(file)

        text = data.get("text")

        with self.subTest("Non-empty response"):
            self.assertTrue(text)

        with self.subTest("Correct OCR output"):
            self.assertIn("Moniteur belge", text)

        xml = data.get("xml")

        with self.subTest("PageXML output"):
            self.assertTrue(xml, "No output")
            self.assertIn(
                "http://schema.primaresearch.org/PAGE",
                xml,
                "Should contain PAGE XML namespace",
            )