import io
import unittest

from fastapi.testclient import TestClient

from app.api.options.general import Option
from app.api.options.line_joiner import Dehypenation, JoinTextLines
from app.core.config import settings
from app.main import app
from app.schemas.schema import ProcessOptions, ProcessPipelineResponse, TextOptionsBase

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
SUBTEST_RESPONSE_TEXT = "Response text"
SUBTEST_PROCESSED_TEXT = "Processed text"


class GetOptionsTest(unittest.TestCase):
    def setUp(self) -> None:
        url = app.url_path_for("pipeline:options")
        self.response = client.get(url)

    def test_get(self):
        with self.subTest(SUBTEST_STATUS_CODE):
            self.assertEqual(self.response.status_code, 200)

        with self.subTest("Response - 1: options"):
            self.assertIn("options", self.response.json())
            options = self.response.json()["options"]

        with self.subTest("Response - 2: name"):
            for option in options:
                self.assertIn("name", option)
                self.assertIsInstance(option["name"], str)

        with self.subTest("Response - 3: metadata"):
            for option in options:
                self.assertIn("description", option)
                self.assertIsInstance(option["description"], str)


class PostProcess(unittest.TestCase):
    def setUp(self) -> None:
        self.url = app.url_path_for("pipeline:process")

        self.url_options = app.url_path_for("pipeline:options")

    def test_post_no_options(self):
        response = client.post(
            self.url,
            json=ProcessOptions(lines=TEXT, language="en").dict(),
        )

        with self.subTest(SUBTEST_STATUS_CODE):
            self.assertEqual(response.status_code, 200)

        data = ProcessPipelineResponse(**response.json())
        sentences = data.lines
        with self.subTest(SUBTEST_PROCESSED_TEXT):
            self.assertListEqual(sentences, TEXT, "Text should not be processed")

    def test_all_options(self):
        response_all = client.get(self.url_options)
        options = [d["name"] for d in response_all.json()["options"]]

        response = client.post(
            self.url,
            json=ProcessOptions(lines=TEXT, language="en", options=options).dict(),
        )

        with self.subTest(SUBTEST_STATUS_CODE):
            self.assertEqual(response.status_code, 200)

        data = ProcessPipelineResponse(**response.json())
        sentences = data.lines
        with self.subTest(SUBTEST_PROCESSED_TEXT):
            self.assertListEqual(sentences, SENTENCES, "Text should be processed")

    def test_post_option_dehypenation(self):
        option = Dehypenation()

        self._test_get_option(
            option=option,
            name="dehyphenation",
            description="Fix hyphenation of words split over multiple lines",
        )

        # Join - dehyphenation
        text_dehyp = []

        # If - is at the end of the line, join with next line
        b_join = False
        for line in TEXT:
            if b_join:
                text_dehyp[-1] = text_dehyp[-1][:-1] + line
                b_join = False
            else:
                text_dehyp.append(line)

            if line.endswith("-"):
                b_join = True

        self._test_post_option(option, text_dehyp)

    def test_post_option_text_join(self):
        option = JoinTextLines()

        self._test_get_option(
            option=option,
            name="join_lines",
            description="Join text lines into a single text",
        )

        text_joined = [" ".join(TEXT)]

        self._test_post_option(option, text_joined)

    def test_process_not_existing(self):
        process = "not_existing"
        response = client.post(
            self.url,
            json=ProcessOptions(lines=TEXT, language="en", options=[process]).dict(),
        )

        with self.subTest(SUBTEST_STATUS_CODE):
            self.assertEqual(response.status_code, 400)

    def _test_get_option(self, option: Option, name: str, description: str):
        with self.subTest("Get option"):
            """Check that option is available"""

            option_dict = option.dict()

            options = self.response_options = client.get(self.url_options).json()[
                "options"
            ]

            with self.subTest("In options"):
                self.assertIn(option_dict, options)

            self.assertEqual(option_dict.get("name"), name)
            self.assertEqual(
                option_dict.get("description"),
                description,
            )

    def _test_post_option(self, option, text_true):
        response = client.post(
            self.url,
            json=ProcessOptions(
                lines=TEXT, language="en", options=[option.name]
            ).dict(),
        )

        with self.subTest(SUBTEST_STATUS_CODE):
            self.assertEqual(response.status_code, 200)

        data = ProcessPipelineResponse(**response.json())
        text_processed = data.lines

        with self.subTest(SUBTEST_PROCESSED_TEXT):
            self.assertListEqual(text_processed, text_true)
