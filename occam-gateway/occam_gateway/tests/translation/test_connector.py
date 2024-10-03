import io
import os
import unittest
import urllib.parse

from translation.connector import CEFETranslationConnector

FILENAME_TEXT = "../test_data/test.txt"
FILENAME_TEXT = os.path.join(os.path.dirname(__file__), FILENAME_TEXT)


class TestCEFLocalOcrConnector(unittest.TestCase):
    """
    Integration tests of CEF eTranslation connector
    """

    def setUp(self) -> None:
        self.connector = CEFETranslationConnector()

    def test_health(self):
        """
        Test that the health check works
        """

        health = self.connector.health()

        with self.subTest("Health"):
            self.assertTrue(health, "Health check failed")

    def test_snippet_translation(self):
        """
        Test that a user can translate a snippet
        """

        snippet = "This is a some text.\nOr is it?"

        translation = self.connector.translate_snippet(snippet, "en", "nl")

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

        with open(FILENAME_TEXT, "rb") as file:
            translation = self.connector.translate_file(file, "en", "nl")

        translation_gt = b"Dit is een voorbeeld. \nOf is dat?"

        with self.subTest("Non-empty response"):
            self.assertTrue(translation, "No translation")

        with self.subTest("Type"):
            self.assertIsInstance(translation, bytes)

        with self.subTest("Correct translation"):
            self.assertEqual(translation, translation_gt)

    def test_snippet_translation_empty(self):
        """
        Test empty snippet translation
        """

        snippet = " \n"

        with self.subTest("Sanity check - not working"):
            url = urllib.parse.urljoin(self.connector.URL, "translate/snippet/blocking")

            with self.assertRaises(Exception):
                self.connector.handle_post_request(
                    url, data={"source": "en", "target": "fr", "snippet": snippet}
                )

        translation = self.connector.translate_snippet(snippet, "en", "nl")

        with self.subTest("Type"):
            self.assertIsInstance(translation, str)

        with self.subTest("Correct"):
            self.assertEqual(translation, snippet)

    def test_file_translation_empty(self):
        """
        Test empty file translation
        """

        content = b" \n"

        with io.BytesIO() as f:
            f.write(content)
            f.seek(0)
            translation = self.connector.translate_file(
                ("filename.txt", f, "text/plain"), "en", "nl"
            )

        with self.subTest("Type"):
            self.assertIsInstance(translation, bytes)

        with self.subTest("Correct translation"):
            self.assertEqual(translation, content)

    def test_connection_error_ngrok(self):
        """
        Test that we get a connection error when the API url is incorrect
        """

        self._test_connection_error("https://12345.ngrok-free.app")

    def test_connection_error_localhost(self):
        """
        Test that we get a connection error when the API url is incorrect
        """

        self._test_connection_error("http://localhost:12345")

    def _test_connection_error(self, url):
        """
        Test that we get a connection error when the API url is incorrect
        """

        self.connector.URL = url

        with self.subTest("Snippet"):
            with self.assertRaises(ConnectionError):
                self.connector.translate_snippet("This is a test", "en", "nl")

        with self.subTest("File"):
            with self.assertRaises(ConnectionError):
                with open(FILENAME_TEXT, "rb") as file:
                    self.connector.translate_file(file, "en", "nl")
