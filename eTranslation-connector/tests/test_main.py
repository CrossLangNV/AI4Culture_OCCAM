import io
import os
import unittest

from fastapi.testclient import TestClient

from app.main import app


@app.on_event("startup")
class MainTest(unittest.TestCase):
    def test_snippet_translation(self):
        """
        Test that a user can translate a snippet
        """

        snippet = "This is a some text.\nOr is it?"

        url = "translate/snippet/blocking"

        with TestClient(app) as client:
            response = client.post(
                url, data={"source": "en", "target": "nl", "snippet": snippet}
            )

        translation = response.json()

        translation_gt = "Dit is een deel van de tekst. \nOf is dat?"

        with self.subTest("Non-empty response"):
            self.assertTrue(translation, "No translation")

        with self.subTest("Type"):
            self.assertIsInstance(translation, str)

        with self.subTest("Correct translation"):
            self.assertEqual(translation, translation_gt)

    def test_file_translation(self):
        """
        Test that a user can translate a file
        """

        FILENAME_TEXT = os.path.join(os.path.dirname(__file__), "data/test.txt")

        url = "translate/document/blocking"

        with open(FILENAME_TEXT, "rb") as file:
            files = {"file": file}

            with TestClient(app) as client:
                response_translate_file = client.post(
                    url, files=files, data={"source": "en", "target": "nl"}
                )

        translation_gt = b"Dit is een voorbeeld. \nOf is dat?"
        translation = response_translate_file.content

        with self.subTest("Non-empty response"):
            self.assertTrue(translation, "No translation")

        with self.subTest("Type"):
            self.assertIsInstance(translation, bytes)

        with self.subTest("Correct translation"):
            self.assertEqual(translation, translation_gt)
