import os.path
import tempfile
import urllib
import warnings
import zipfile
from unittest import mock

import django.test
from django.urls import reverse
from lxml import etree
from rest_framework import status

from organisation.models import OrganisationAPIKey
from shared.models import StatusField
from shared.pipeline import PageXMLWrapper, PipelineStepEnum
from tests.organisation.utils import create_test_api_headers
from tests.shared.utils_test_views import SharedTestAPIPermission
from translation.models import UsageTranslationFile, UsageTranslationSnippet
from translation.views import (
    TranslatePipelineAPIView,
    TranslatePipelineOptionsAPIView,
    TranslateSnippetAPIView,
)

FILENAME_TEXT = os.path.join(os.path.dirname(__file__), "../test_data", "test.txt")
FILENAME_XML = os.path.join(os.path.dirname(__file__), "../test_data", "ocr.xml")
FILENAME_XML_PAGE = os.path.join(os.path.dirname(__file__), "../test_data", "ocr.page")


for filename in [FILENAME_TEXT]:
    if not os.path.exists(filename):
        warnings.warn(f"File {filename} does not exist for testing OCR")


def mock_translate_snippet(*args, **kwargs) -> str:
    return "FOO to the BAR.\n"


def mock_translate_file(_self, file, source, target) -> bytes:
    if isinstance(file, tuple):
        file = file[1]

    s = file.read()

    # if not s:
    #     return b""

    s_mock = "".join(
        [line.decode("utf-8").upper() + " MOCK\n" for line in s.splitlines()]
    )
    return s_mock.encode("utf-8")


@mock.patch(
    "translation.connector.CEFETranslationConnector.translate_snippet",
    mock_translate_snippet,
)
class TranslateSnippetAPIViewTest(django.test.TestCase, SharedTestAPIPermission):
    NAMESPACE = "translation"
    VIEWNAME = "snippet"

    def setUp(self) -> None:
        self.url = reverse(f"{self.NAMESPACE}:{self.VIEWNAME}")
        self.view = TranslateSnippetAPIView()

        # Login
        self.headers = create_test_api_headers()

    def test_post(self):
        text = "This is a test file."

        response = self.client.post(
            self.url,
            headers=self.headers,
            data={"snippet": text, "source": "en", "target": "nl"},
        )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        translated_text = response.json()

        with self.subTest("Non-empty response"):
            self.assertTrue(translated_text)

        with self.subTest("Expected response"):
            self.assertEqual("FOO to the BAR.\n", translated_text)

        with self.subTest("Usage"):
            # Get last usage
            usage = UsageTranslationSnippet.objects.last()
            self.assertEqual(usage.source_size, len(text), "Source size not set")
            self.assertEqual(
                usage.target_size, len(translated_text), "Target size not set"
            )
            self.assertEqual(usage.status, StatusField.SUCCESS)

            mock_request = mock.Mock()
            mock_request.META = response.request
            self.assertEqual(
                usage.api_key,
                OrganisationAPIKey.objects.get_from_request(mock_request),
            )


@mock.patch(
    "translation.connector.CEFETranslationConnector.translate_file",
    mock_translate_file,
)
class TranslateFileAPIViewTest(django.test.TestCase, SharedTestAPIPermission):
    NAMESPACE = "translation"
    VIEWNAME = "file"

    def setUp(self) -> None:
        self.url = reverse(f"{self.NAMESPACE}:{self.VIEWNAME}")
        self.view = TranslateSnippetAPIView()

        # Login
        self.headers = create_test_api_headers()

    def test_post(self):
        with open(FILENAME_TEXT, "rb") as file:
            response = self.client.post(
                self.url,
                headers=self.headers,
                data={"file": file, "source": "en", "target": "nl"},
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        translated_file = response.content

        with self.subTest("Non-empty response"):
            self.assertTrue(translated_file)

        with self.subTest("Expected response"):
            with open(FILENAME_TEXT, "rb") as file:
                self.assertEqual(
                    mock_translate_file(None, file, None, None), translated_file
                )

        with self.subTest("Usage"):
            # Get last usage
            with open(FILENAME_TEXT, "rb") as file:
                # File size
                file_size = len(file.read())

            usage = UsageTranslationFile.objects.last()
            self.assertEqual(usage.source_size, file_size, "Source size not set")
            self.assertEqual(
                usage.target_size, len(translated_file), "Target size not set"
            )
            self.assertEqual(usage.status, StatusField.SUCCESS)

            mock_request = mock.Mock()
            mock_request.META = response.request
            self.assertEqual(
                usage.api_key,
                OrganisationAPIKey.objects.get_from_request(mock_request),
            )


@mock.patch(
    "translation.connector.CEFETranslationConnector.translate_file",
    mock_translate_file,
)
class TranslatePipelineAPIViewTest(django.test.TestCase, SharedTestAPIPermission):
    NAMESPACE = "translation"
    VIEWNAME = "pipeline"

    def setUp(self) -> None:
        self.url = reverse(f"{self.NAMESPACE}:{self.VIEWNAME}")
        self.view = TranslatePipelineAPIView()

        # Login
        self.headers = create_test_api_headers()

    def test_post(self):
        with open(FILENAME_XML, "rb") as file:
            response = self.client.post(
                self.url,
                headers=self.headers,
                data={"file": file, "source": "nl", "target": "en"},
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        translated_file = response.content

        with self.subTest("Non-empty response"):
            self.assertTrue(translated_file)

        with self.subTest("Expected response"):
            self.assertIn(b"MOCK", translated_file)
            self.assertIn(
                b"http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15",
                translated_file,
                "PAGE XML namespace not present",
            )

        if 0:
            with self.subTest("Usage"):
                self.assertEqual(0, 1, "Not implemented")

    def test_content_type_xml(self):
        """
        Is the content type still recognized as XML if I change the extension?
        """

        with open(FILENAME_XML_PAGE, "rb") as file:
            # Mock file extension
            response = self.client.post(
                self.url,
                headers=self.headers,
                data={
                    "file": file,
                    "source": "nl",
                    "target": "en",
                },
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        with self.subTest("Content type"):
            self.assertEqual(
                "application/xml",
                response["Content-Type"],
                "Content type not recognized as XML",
            )

        translated_file = response.content
        with self.subTest("Expected response"):
            self.assertIn(b"MOCK", translated_file)
            self.assertIn(
                b"http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15",
                translated_file,
                "PAGE XML namespace not present",
            )

    def test_text(self):
        """
        When a flat text is passed, the text should be translated.
        :return:
        """

        with open(FILENAME_TEXT, "rb") as file:
            response = self.client.post(
                self.url,
                headers=self.headers,
                data={"file": file, "source": "nl", "target": "en"},
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        translated_file = response.content

        with self.subTest("Non-empty response"):
            self.assertTrue(translated_file)

        with self.subTest("Expected response"):
            self.assertIn(b"MOCK", translated_file)

        with self.subTest("No XML"):
            self.assertNotIn(
                b"<",
                translated_file,
            )
            self.assertNotIn(
                b">",
                translated_file,
            )

        with open(FILENAME_TEXT, "r") as file:
            orig_text = file.read()

        with self.subTest("Equal content"):
            lines_orig = orig_text.splitlines()
            lines_translated = translated_file.decode("utf-8").splitlines()

            self.assertEqual(
                len(lines_orig), len(lines_translated), "Different number of lines"
            )

            for i, (line_orig, line_translated) in enumerate(
                zip(lines_orig, lines_translated)
            ):
                # Check empty lines
                if not line_orig:
                    self.assertEqual("", line_translated)
                    continue
                else:
                    self.assertNotEqual("", line_translated)

    @mock.patch("shared.pipeline.SegmentationStep.backward")
    @mock.patch("shared.pipeline.SegmentationStep.forward")
    def test_default_options(
        self,
        mock_segmentation_forward,
        mock_segmentation_backward,
    ):
        mock_segmentation_forward.side_effect = lambda x: x
        mock_segmentation_backward.side_effect = lambda x: x

        with open(FILENAME_XML, "rb") as file:
            response = self.client.post(
                self.url,
                headers=self.headers,
                data={
                    "file": file,
                    "source": "nl",
                    "target": "en",
                },
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        with self.subTest("Non-empty response"):
            self.assertTrue(response.content)

        with self.subTest("Segmentation called once"):
            mock_segmentation_forward.assert_called_once()
            mock_segmentation_backward.assert_called_once()

    @mock.patch("shared.pipeline.SegmentationStepShared.backward")
    @mock.patch("shared.pipeline.SegmentationStepShared.forward")
    @mock.patch("shared.pipeline.OCRCorrectionLLMFlairStep.forward")
    def test_all_options_manual(
        self,
        mock_correction_forward,
        mock_segmentation_forward,
        mock_segmentation_backward,
    ):
        for mock_f in [
            mock_correction_forward,
            mock_correction_forward,
            mock_segmentation_forward,
        ]:
            mock_f.side_effect = lambda x: x

        options = PipelineStepEnum.get_names()
        options_str = ", ".join(options)

        with open(FILENAME_XML, "rb") as file:
            response = self.client.post(
                self.url,
                headers=self.headers,
                data={
                    "file": file,
                    "source": "nl",
                    "target": "en",
                    "options": options_str,
                },
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        with self.subTest("Non-empty response"):
            self.assertTrue(response.content)

        with self.subTest("Segmentation called"):
            mock_segmentation_forward.assert_called()
            mock_segmentation_backward.assert_called()

    @mock.patch("shared.pipeline.SegmentationStep.backward")
    @mock.patch("shared.pipeline.SegmentationStep.forward")
    def test_no_options_manual(
        self,
        mock_segmentation_forward,
        mock_segmentation_backward,
    ):
        mock_segmentation_forward.side_effect = lambda x: x
        mock_segmentation_backward.side_effect = lambda x: x

        options_str = ""

        with open(FILENAME_XML, "rb") as file:
            response = self.client.post(
                self.url,
                headers=self.headers,
                data={
                    "file": file,
                    "source": "nl",
                    "target": "en",
                    "options": options_str,
                },
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        with self.subTest("Non-empty response"):
            self.assertTrue(response.content)

        with self.subTest("Segmentation not called"):
            mock_segmentation_forward.assert_not_called()
            mock_segmentation_backward.assert_not_called()

    def test_option_not_found(self):
        options_str = "foo, bar"

        with open(FILENAME_XML, "rb") as file:
            response = self.client.post(
                self.url,
                headers=self.headers,
                data={
                    "file": file,
                    "source": "nl",
                    "target": "en",
                    "options": options_str,
                },
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        with self.subTest("Info"):
            self.assertIn(
                "Options not found", response.json()["error"], response.json()
            )

    def test_dont_reconstruct(self):
        with open(FILENAME_XML, "rb") as file:
            response = self.client.post(
                self.url,
                headers=self.headers,
                data={
                    "file": file,
                    "source": "nl",
                    "target": "en",
                    "options": "",  # No options for faster testing
                    "reconstruct": False,
                },
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        translated_text = response.content.decode("utf-8")

        with self.subTest("Non-empty response"):
            self.assertTrue(translated_text)

        with self.subTest("Correct translation output"):
            self.assertIn("MOCK", translated_text)

        with self.subTest("Text content type"):
            self.assertEqual("text/plain", response["Content-Type"])

        with self.subTest("flat text"):
            # Should fail
            with self.assertRaises(etree.XMLSyntaxError):
                self._test_validate_PAGE(translated_text)

            self.assertNotIn("PcGts", translated_text)
            self.assertNotIn("TextRegion", translated_text)

            self.assertNotIn("[", translated_text)
            self.assertNotIn("]", translated_text)

        with self.subTest("Usage"):
            page_xml_in = PageXMLWrapper()
            page_xml_in.parse(FILENAME_XML)

            # Get last usage
            usage = UsageTranslationFile.objects.last()
            self.assertTrue(usage, "Usage not created")

            text_in_size = sum(
                [
                    len(line)  # Don't count newlines, else +1
                    for paragraph in page_xml_in.get_paragraphs()
                    for line in paragraph
                ]
            )

            text_out_size = (
                sum(
                    [
                        len(line) + 5  # From mock translate
                        for paragraph in page_xml_in.get_paragraphs()
                        for line in paragraph
                    ]
                )
                - 1
            )  # One off error, ignore

            self.assertEqual(text_in_size, usage.source_size, "Source size mismatch")
            self.assertEqual(text_out_size, usage.target_size, "Target size mismatch")
            self.assertEqual(usage.status, StatusField.SUCCESS)

            mock_request = mock.Mock()
            mock_request.META = response.request
            self.assertEqual(
                usage.api_key,
                OrganisationAPIKey.objects.get_from_request(mock_request),
            )

    def _test_validate_PAGE(self, xml):
        tree = etree.fromstring(xml.encode("utf-8"))
        xmlns = tree.tag.split("}")[0].strip("{")

        url = urllib.parse.urljoin(xmlns + "/", "pagecontent.xsd")
        # url = "https://www.primaresearch.org/schema/PAGE/gts/pagecontent/2019-07-15/pagecontent.xsd"

        response = urllib.request.urlopen(url).read()
        xmlschema_doc = etree.fromstring(response)
        xmlschema = etree.XMLSchema(xmlschema_doc)

        xmlschema.assertValid(tree)


class TranslatePipelineOptionsAPIViewTest(
    django.test.TestCase, SharedTestAPIPermission
):
    def setUp(self):
        self.url = reverse("translation:pipeline_options")
        self.view = TranslatePipelineOptionsAPIView()

        # Login
        self.headers = create_test_api_headers()

    def test_get_all(self):
        response = self.client.get(self.url, headers=self.headers)

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        options = response.json()

        step_representation = PipelineStepEnum.get_representation()

        with self.subTest("Non-empty response"):
            self.assertTrue(options)

        with self.subTest("Response format"):
            """
            [{"name": <name>, "description": <description>}, ...]
            """
            self.assertIsInstance(options, list)
            for option in options:
                self.assertIsInstance(option, dict)
                self.assertIn("name", option)
                self.assertIn("description", option)
                self.assertIsInstance(option["name"], str)
                self.assertIsInstance(option["description"], str)

        with self.subTest("Names"):
            option_names = [option["name"] for option in options]
            for pipeline_step in PipelineStepEnum:
                self.assertIn(pipeline_step.value.name, option_names)

        with self.subTest("Expected response"):
            self.assertListEqual(step_representation, options)


@mock.patch("shared.pipeline.OCRCorrectionStep.backward", lambda self, x: x)
@mock.patch("shared.pipeline.OCRCorrectionStep.forward", lambda self, x: x)
@mock.patch("shared.pipeline.SegmentationStep.backward", lambda self, x: x)
@mock.patch("shared.pipeline.SegmentationStep.forward", lambda self, x: x)
@mock.patch(
    "translation.connector.CEFETranslationConnector.translate_file",
    mock_translate_file,
)
class TranslatePipelineBatchAPIViewTest(django.test.TestCase, SharedTestAPIPermission):
    NAMESPACE = "translation"
    VIEWNAME = "pipeline_batch"

    def setUp(self) -> None:
        self.url = reverse(f"{self.NAMESPACE}:{self.VIEWNAME}")
        self.view = TranslatePipelineBatchAPIViewTest()

        # Login
        self.headers = create_test_api_headers()

    def test_post(self):
        # Create zip with files
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_filename = os.path.join(temp_dir, "test.zip")
            with zipfile.ZipFile(zip_filename, "w") as zip_file:
                zip_file.write(FILENAME_XML, os.path.basename(FILENAME_XML))
                zip_file.write(FILENAME_TEXT, os.path.basename(FILENAME_TEXT))

            with open(zip_filename, "rb") as file:
                response = self.client.post(
                    self.url,
                    headers=self.headers,
                    data={"file": file, "source": "nl", "target": "en"},
                )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code, response.content)

        with tempfile.TemporaryDirectory() as temp_dir:
            zip_filename = os.path.join(temp_dir, "test.zip")
            with open(zip_filename, "wb") as f:
                f.write(response.content)

            with zipfile.ZipFile(zip_filename, "r") as zip_file:
                zip_file.extractall(temp_dir)

            with open(
                os.path.join(temp_dir, os.path.basename(FILENAME_XML)), "rb"
            ) as file:
                translated_file = file.read()

            with self.subTest("Expected response"):
                self.assertIn(b"MOCK", translated_file)
                self.assertIn(
                    b"http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15",
                    translated_file,
                    "PAGE XML namespace not present",
                )
