import html as html_package
import os

import django.test
from django.urls import reverse
from rest_framework import status

from evaluation.views import OCREvalAPIView
from tests.organisation.utils import create_test_api_headers

FILENAME_OCR = "ocr.xml"
FILENAME_OCR_GT = "ocr_gt.xml"

DIR_DATA = os.path.join(os.path.dirname(__file__), "../test_data")
FILENAME_OCR = os.path.join(DIR_DATA, FILENAME_OCR)
FILENAME_OCR_GT = os.path.join(DIR_DATA, FILENAME_OCR_GT)

assert os.path.exists(FILENAME_OCR), f"File not found: {FILENAME_OCR}"
assert os.path.exists(FILENAME_OCR_GT), f"File not found: {FILENAME_OCR_GT}"


class OCREvalAPIViewTest(django.test.TestCase):
    NAMESPACE = "evaluation"
    VIEWNAME = "OCR-eval"

    def setUp(self) -> None:
        self.url = reverse(f"{self.NAMESPACE}:{self.VIEWNAME}")
        self.view = OCREvalAPIView()

        # Login
        self.headers = create_test_api_headers()

    def test_eval(self):
        """ """

        with open(FILENAME_OCR, "rb") as file_ocr, open(
            FILENAME_OCR_GT, "rb"
        ) as file_gt:
            response = self.client.post(
                self.url,
                headers=self.headers,
                data={"file_ocr": file_ocr, "file_gt": file_gt},
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        html = b"".join(response.streaming_content).decode("utf-8")

        with self.subTest("Content"):
            self.assertTrue(html)

        with self.subTest("CER score"):
            # Find "CER: <score>"
            start = html.find("CER: ") + 5
            end = html.find("</p>", start)
            score = html[start:end].strip()
            score = float(score)
            self.assertGreater(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_encoding(self):
        """
        22/05/2024: Special characters become wrongly encoded in the report
        """

        FILENAME_SPECIAL = os.path.join(DIR_DATA, "BC_sym_10.txt")

        with open(FILENAME_SPECIAL, "rb") as file:
            raw_bytes = file.read()

        # Open twice to avoid issues
        with open(FILENAME_SPECIAL) as file1, open(FILENAME_SPECIAL) as file2:
            response = self.client.post(
                self.url,
                headers=self.headers,
                data={"file_ocr": file1, "file_gt": file2},
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        html_raw = b"".join(response.streaming_content)
        html = html_raw.decode("utf-8")

        with self.subTest("Content"):
            self.assertTrue(html)

        with self.subTest("Encoding"):
            self.assertIn("utf-8", html)

        special_chars_in = [
            # b"\xe2\x80\x99" # Is converted to an escaped single qoute
            b"'",
        ]

        special_chars_not = [
            b"\xe2\x82\xac",
            b"\xe2\x84\xa2",
        ]

        with self.subTest("Special characters - Sanity check"):
            # for char in special_chars_in:
            #     self.assertIn(char, raw_bytes)

            for char in special_chars_not:
                self.assertNotIn(char, raw_bytes)

        # Bugs reported:
        with self.subTest("Special characters - in"):
            for char in special_chars_in:
                self.assertIn(
                    char.decode("utf-8"),
                    html_package.unescape(html_raw.decode("utf-8")),
                )

        with self.subTest("Special characters - not in"):
            for char in special_chars_not:
                self.assertNotIn(char.decode("utf-8"), html)


class OCREvalTextAPIViewTest(django.test.TestCase):
    NAMESPACE = "evaluation"
    VIEWNAME = "OCR-eval-text"

    def setUp(self) -> None:
        self.url = reverse(f"{self.NAMESPACE}:{self.VIEWNAME}")
        self.view = OCREvalAPIView()

        # Login
        self.headers = create_test_api_headers()

    def test_eval(self):
        response = self.client.post(
            self.url,
            headers=self.headers,
            data={
                "text_ocr": "test\nSome example text.",
                "text_gt": "text\nSome example test.",
            },
        )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code, response.content)

        results = response.json()
        with self.subTest("Content"):
            self.assertTrue(results)

        with self.subTest("CER score"):
            score = results["cer"]
            self.assertGreater(score, 0.0)
            self.assertLessEqual(score, 1.0)
            self.assertAlmostEqual(score, 0.0869, delta=0.0001)

        with self.subTest("WER score"):
            score = results["wer"]
            self.assertEqual(score, 2 / 4)

        char_diffs = results["differences"]["character_level"]
        with self.subTest("Character level differences"):
            self.assertEqual(2, len(char_diffs))

            self.assertIn("s :: x", char_diffs)
            self.assertIn("x :: s", char_diffs)

    def test_encoding(self):
        """
        22/05/2024: Special characters become wrongly encoded in the report
        """

        text = "a c d"
        bytes_special_characters = b"a\xe2\x80\x99c d"
        text_special_characters = bytes_special_characters.decode("utf-8")

        response = self.client.post(
            self.url,
            headers=self.headers,
            data={
                "text_ocr": text,
                "text_gt": text_special_characters,
            },
        )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        report = response.json()

        with self.subTest("chars"):
            self.assertEqual(5, report["n_characters"])

        char_level = report["differences"]["character_level"]
        word_level = report["differences"]["word_level"]

        with self.subTest("differences - char"):
            self.assertEqual(1, len(char_level), char_level)

        with self.subTest("differences - word"):
            self.assertEqual(0, len(word_level), word_level)

        with self.subTest("CER"):
            self.assertEqual(1 / 5, report["cer"])

        with self.subTest("WER"):
            self.assertEqual(0, report["wer"])

        special_chars_in = [
            # b"\xe2\x80\x99" # Is converted to an escaped single qoute
            b"'",
        ]

        special_chars_not = [
            b"\xe2\x82\xac",
            b"\xe2\x84\xa2",
        ]

        edits = ";".join(char_level.keys())

        with self.subTest("Special characters - in"):
            for char in special_chars_in:
                self.assertIn(char.decode("utf-8"), edits)

        with self.subTest("Special characters - not in"):
            for char in special_chars_not:
                self.assertNotIn(char.decode("utf-8"), edits)
