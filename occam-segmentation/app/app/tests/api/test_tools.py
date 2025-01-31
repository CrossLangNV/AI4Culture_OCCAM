import io
import unittest

from fastapi.testclient import TestClient

from app.api.options.general import Option
from app.api.options.line_joiner import Dehypenation, JoinTextLines
from app.core.config import settings
from app.main import app
from app.schemas.schema import (
    ProcessOptions,
    ProcessPipelineResponse,
    ProcessResponse,
    TextOptionsBase,
)

client = TestClient(app)


TEXT = [
    "This is a sent-",
    "ence. This is",
    "another sentence.",
    "As you can see, it",
    "is split over multi-",
    "ple lines.",
]

SENTENCES = [
    "This is a sentence.",
    "This is another sentence.",
    "As you can see, it is split over multiple lines.",
]

SUBTEST_STATUS_CODE = "Status code"
SUBTEST_RESPONSE_MODEL = "Response - Parsing"
SUBTEST_RESPONSE_TEXT = "Response - Processed text"


class PostExtractSentencesFromLinesTest(unittest.TestCase):
    def setUp(self):
        self.url = app.url_path_for("tools:sentences_from_lines")

    def test_post(self):
        response = client.post(
            self.url,
            json=TextOptionsBase(lines=TEXT, language="en").dict(),
        )

        with self.subTest(SUBTEST_STATUS_CODE):
            self.assertEqual(response.status_code, 200)

        with self.subTest(SUBTEST_RESPONSE_MODEL):
            data = ProcessResponse(**response.json())

        with self.subTest(SUBTEST_RESPONSE_TEXT):
            self.assertListEqual(data.lines, SENTENCES)


class PostExtractSentencesFromLinesFileTest(unittest.TestCase):
    def setUp(self):
        self.url = app.url_path_for("tools:sentences_from_lines:file")

    def test_post(self):
        with io.BytesIO("\n".join(TEXT).encode()) as f:
            response = client.post(
                self.url,
                files={"file": ("text_file.txt", f, "text/plain")},
                params={"language": "en"},
            )

        with self.subTest(SUBTEST_STATUS_CODE):
            self.assertEqual(response.status_code, 200)

        sentences = response.text.splitlines()
        with self.subTest(SUBTEST_RESPONSE_TEXT):
            self.assertListEqual(sentences, SENTENCES)

        with self.subTest("filename"):
            self.assertEqual(
                response.headers["Content-Disposition"],
                "attachment; filename=text_file_sentences.txt",
            )


class PostOkapiSegmentationTest(unittest.TestCase):
    def setUp(self):
        self.url = app.url_path_for("tools:okapi_segmentation")

        # Split sentences at ". "
        self.text_ref = "\n".join(TEXT).replace(". ", ".\n").splitlines()

    def test_post(self):
        response = client.post(
            self.url,
            json=TextOptionsBase(lines=TEXT, language="en").dict(),
        )

        with self.subTest(SUBTEST_STATUS_CODE):
            self.assertEqual(response.status_code, 200)

        with self.subTest(SUBTEST_RESPONSE_MODEL):
            data = ProcessResponse(**response.json())

        with self.subTest(SUBTEST_RESPONSE_TEXT):
            self.assertListEqual(data.lines, self.text_ref)


if __name__ == "__main__":
    unittest.main()
