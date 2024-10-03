import os
import zipfile
from io import BytesIO
from unittest import mock

import requests
from django.urls import reverse
from lxml import etree
from rest_framework import status
from rest_framework.test import APITestCase

from ocr.models import OCREngine, UsageOCR
from organisation.models import Organisation, OrganisationAPIKey
from shared.models import StatusField
from shared.pipeline import PipelineStepEnum
from tests.shared.utils_test_views import SharedTestAPIPermission

# Constants for test files
FILENAME_IMAGE = os.path.join(os.path.dirname(__file__), "test_image.jpg")
DIRNAME_DATA = os.path.join(os.path.dirname(__file__), "../test_data")
FILENAME_PDF_MR = os.path.join(DIRNAME_DATA, "example_machine_readable.pdf")
FILENAME_PDF_SCAN = os.path.join(DIRNAME_DATA, "example_scanned.pdf")

# Ensure test files exist
for filename in [FILENAME_IMAGE, FILENAME_PDF_MR, FILENAME_PDF_SCAN]:
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Test file {filename} does not exist.")

# Load the PAGE XML schema from local file
SCHEMA_FILENAME = os.path.join(DIRNAME_DATA, "pagecontent.xsd")
if not os.path.exists(SCHEMA_FILENAME):
    raise FileNotFoundError(f"Schema file {SCHEMA_FILENAME} does not exist.")
with open(SCHEMA_FILENAME, "rb") as f:
    XML_SCHEMA_DOC = etree.parse(f)
XML_SCHEMA = etree.XMLSchema(XML_SCHEMA_DOC)


def mock_ocr_image(*args, **kwargs):
    response_json = {
        "name": "ocr_example.png",
        "xml": '''
<PcGts xmlns="http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xsi:schemaLocation="http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15 pagecontent.xsd">
  <Metadata>
    <Creator>Pero OCR</Creator>
    <Created>2023-07-10T09:01:36.100227+00:00</Created>
    <LastChange>2023-07-10T09:01:36.100227+00:00</LastChange>
  </Metadata>
  <Page imageFilename="ocr_example.png" imageWidth="1801" imageHeight="190">
    <TextRegion id="r000">
      <Coords points="100,100 0,100"/>
      <TextLine id="r000-l001" index="0">
        <Coords points="0,0 100,0"/>
        <TextEquiv conf="0.997">
          <Unicode>History of Automated Advisories</Unicode>
        </TextEquiv>
      </TextLine>
    </TextRegion>
  </Page>
</PcGts>
        '''
    }
    return response_json


def mock_fetch_image(url, *args, **kwargs):
    if url == "https://example.com/test_image.png":
        with open(FILENAME_IMAGE, "rb") as f:
            content = f.read()
        response = mock.Mock()
        response.status_code = 200
        response.headers = {"Content-Type": "image/png"}
        response.content = content
        return response
    else:
        # Simulate a failed request
        response = mock.Mock()
        response.status_code = 404
        response.raise_for_status.side_effect = requests.HTTPError("404 Client Error: Not Found for url: " + url)
        return response


class OCRShared(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        schema_parser = etree.XMLParser(load_dtd=True, no_network=False)
        with open(SCHEMA_FILENAME, "rb") as f:
            xmlschema_doc = etree.parse(f, parser=schema_parser)
            cls.xmlschema = etree.XMLSchema(xmlschema_doc)

    def validate_page_xml(self, xml):
        """
        Validates the given PAGE XML string against the PAGE XML schema.
        """
        if not xml or not xml.strip():
            self.fail("XML Validation Error: XML content is empty or None.")

        try:
            tree = etree.fromstring(xml.encode("utf-8"))
            self.xmlschema.assertValid(tree)
        except (etree.XMLSyntaxError, etree.DocumentInvalid) as e:
            self.fail(f"XML Validation Error: {e}")


class OCREngineListViewTest(APITestCase):
    NAMESPACE = "OCR"
    VIEWNAME = "engines"

    def setUp(self):
        self.url = reverse(f"{self.NAMESPACE}:{self.VIEWNAME}")

        # Create an organisation
        self.organisation = Organisation.objects.create(name='Test Org')

        # Create an API key
        _, self.api_key = OrganisationAPIKey.objects.create_key(
            name='Test Key',
            organisation=self.organisation,
        )

        # Set the authentication credentials
        self.client.credentials(HTTP_API_KEY=self.api_key)

        # Ensure at least one OCR engine exists
        if not OCREngine.objects.exists():
            OCREngine.objects.create(name="Test Engine")

    def test_get_engines(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data)
        self.assertEqual(OCREngine.objects.count(), len(response.data))

    def test_non_auth(self):
        # Remove authentication credentials
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@mock.patch("ocr.connector.LocalOcrConnector.ocr_image", mock_ocr_image)
class OCRAPIViewTest(OCRShared):
    NAMESPACE = "OCR"
    VIEWNAME = "image"

    def setUp(self):
        self.url = reverse(f"{self.NAMESPACE}:{self.VIEWNAME}")

        # Create an organisation
        self.organisation = Organisation.objects.create(name='Test Org')

        # Create an API key
        _, self.api_key = OrganisationAPIKey.objects.create_key(
            name='Test Key',
            organisation=self.organisation,
        )

        # Set the authentication credentials
        self.client.credentials(HTTP_API_KEY=self.api_key)

        # Ensure at least one OCR engine exists
        if not OCREngine.objects.exists():
            OCREngine.objects.create(name="Test Engine")
        self.ocr_engine = OCREngine.objects.first()

    def test_post(self):
        with open(FILENAME_IMAGE, "rb") as file:
            response = self.client.post(
                self.url,
                data={"file": file, "engineId": self.ocr_engine.id},
                format='multipart'
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        xml = response.content.decode("utf-8")
        self.assertIn("History of Automated Advisories", xml)
        self.validate_page_xml(xml)

        usage = UsageOCR.objects.last()
        self.assertGreater(usage.image_size, 0)
        self.assertEqual(usage.status, StatusField.SUCCESS)
        self.assertEqual(usage.ocr_engine, self.ocr_engine)

    def test_invalid_engine(self):
        with open(FILENAME_IMAGE, "rb") as file:
            response = self.client.post(
                self.url,
                data={"file": file, "engineId": 9999},
                format='multipart'
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("OCR engine not found", response.data["error"])


@mock.patch("ocr.connector.LocalOcrConnector.ocr_image", mock_ocr_image)
class OCRFromURLAPIViewTest(OCRShared):
    NAMESPACE = "OCR"
    VIEWNAME = "image_url"

    def setUp(self):
        self.url = reverse(f"{self.NAMESPACE}:{self.VIEWNAME}")

        # Create an organisation
        self.organisation = Organisation.objects.create(name='Test Org')

        # Create an API key
        _, self.api_key = OrganisationAPIKey.objects.create_key(
            name='Test Key',
            organisation=self.organisation,
        )

        # Set the authentication credentials
        self.client.credentials(HTTP_API_KEY=self.api_key)

        # Ensure at least one OCR engine exists
        if not OCREngine.objects.exists():
            OCREngine.objects.create(name="Test Engine")
        self.ocr_engine = OCREngine.objects.first()

    @mock.patch("requests.get", side_effect=mock_fetch_image)
    def test_post(self, mock_requests_get):
        url = "https://example.com/test_image.png"
        response = self.client.post(
            self.url, data={"url": url, "engineId": self.ocr_engine.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        xml = response.content.decode("utf-8")
        self.assertIn("History of Automated Advisories", xml)
        self.validate_page_xml(xml)

    @mock.patch("requests.get", side_effect=mock_fetch_image)
    def test_invalid_url(self, mock_requests_get):
        url = "https://example.com/invalid_image.png"
        response = self.client.post(
            self.url, data={"url": url, "engineId": self.ocr_engine.id}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Failed to fetch image from URL", response.data["error"])

    @mock.patch("requests.get", side_effect=mock_fetch_image)
    def test_invalid_engine(self, mock_requests_get):
        url = "https://example.com/test_image.png"
        response = self.client.post(
            self.url, data={"url": url, "engineId": 9999}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("OCR engine not found", response.data["error"])


@mock.patch("ocr.connector.LocalOcrConnector.ocr_image", mock_ocr_image)
class OCRPDFViewTest(OCRShared):
    NAMESPACE = "OCR"
    VIEWNAME = "pdf"

    def setUp(self):
        self.url = reverse(f"{self.NAMESPACE}:{self.VIEWNAME}")

        # Create an organisation
        self.organisation = Organisation.objects.create(name='Test Org')

        # Create an API key
        _, self.api_key = OrganisationAPIKey.objects.create_key(
            name='Test Key',
            organisation=self.organisation,
        )

        # Set the authentication credentials
        self.client.credentials(HTTP_API_KEY=self.api_key)

        # Ensure at least one OCR engine exists
        if not OCREngine.objects.exists():
            OCREngine.objects.create(name="Test Engine")
        self.ocr_engine = OCREngine.objects.first()

    def test_post(self):
        with open(FILENAME_PDF_SCAN, "rb") as file:
            response = self.client.post(
                self.url, data={"file": file, "engineId": self.ocr_engine.id}, format='multipart'
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        xml_list = self.parse_response(response)
        self.assertEqual(len(xml_list), 6)
        for xml in xml_list:
            self.assertIn("History of Automated Advisories", xml)
            self.validate_page_xml(xml)

    def parse_response(self, response):
        zip_file = response.content
        l_xml = []
        with zipfile.ZipFile(BytesIO(zip_file)) as zip_ref:
            for file in zip_ref.namelist():
                if file.endswith(".xml"):
                    with zip_ref.open(file) as f:
                        xml = f.read().decode("utf-8")
                        l_xml.append(xml)
        return l_xml


@mock.patch("ocr.connector.LocalOcrConnector.ocr_image", mock_ocr_image)
class OCRPipelineAPIViewTest(OCRShared, SharedTestAPIPermission):
    NAMESPACE = "OCR"
    VIEWNAME = "pipeline"

    def setUp(self):
        self.url = reverse(f"{self.NAMESPACE}:{self.VIEWNAME}")

        # Create an organisation
        self.organisation = Organisation.objects.create(name='Test Org')

        # Create an API key
        _, self.api_key = OrganisationAPIKey.objects.create_key(
            name='Test Key',
            organisation=self.organisation,
        )

        # Set the authentication credentials
        self.client.credentials(HTTP_API_KEY=self.api_key)

        # Ensure at least one OCR engine exists
        if not OCREngine.objects.exists():
            OCREngine.objects.create(name="Test Engine")
        self.ocr_engine = OCREngine.objects.first()

    def test_post(self):
        with open(FILENAME_IMAGE, "rb") as file:
            response = self.client.post(
                self.url,
                data={"file": file, "engineId": self.ocr_engine.id},
                format='multipart'
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        xml = response.content.decode("utf-8")

        with self.subTest("Non-empty response"):
            self.assertTrue(xml)

        with self.subTest("Correct OCR output"):
            self.assertIn("History of Automated Advisories", xml)

        with self.subTest("XML content type"):
            self.assertEqual("application/xml", response["Content-Type"])

        with self.subTest("Valid XML"):
            self.validate_page_xml(xml)

        with self.subTest("Usage"):
            # Get last usage
            usage = UsageOCR.objects.last()
            self.assertGreater(usage.image_size, 0, "Image size not set")
            self.assertEqual(usage.overlay_size, len(xml))
            self.assertEqual(usage.status, StatusField.SUCCESS)
            self.assertEqual(usage.ocr_engine, self.ocr_engine)

            mock_request = mock.Mock()
            mock_request.META = response.request
            self.assertEqual(
                usage.api_key,
                OrganisationAPIKey.objects.get_from_request(mock_request),
            )

    @mock.patch("shared.pipeline.JoinAllStep.backward")
    @mock.patch("shared.pipeline.JoinAllStep.forward")
    @mock.patch("shared.pipeline.SegmentationStep.backward")
    @mock.patch("shared.pipeline.SegmentationStep.forward")
    def test_default_options(
            self,
            mock_segmentation_forward,
            mock_segmentation_backward,
            mock_join_all_forward,
            mock_join_all_backward,
    ):
        """
        by default only segmentation is called
        """
        mock_segmentation_forward.side_effect = lambda x: x
        mock_segmentation_backward.side_effect = lambda x: x
        mock_join_all_forward.side_effect = lambda x: x
        mock_join_all_backward.side_effect = lambda x: x

        with open(FILENAME_IMAGE, "rb") as file:
            response = self.client.post(
                self.url,
                data={
                    "file": file,
                    "engineId": self.ocr_engine.id,
                    "source": "nl",
                },
                format='multipart'
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        with self.subTest("Non-empty response"):
            self.assertTrue(response.content)

        with self.subTest("no segmentation called"):
            mock_segmentation_forward.assert_called_once()
            mock_segmentation_backward.assert_called_once()

        with self.subTest("join all NOT called"):
            mock_join_all_forward.assert_not_called()
            mock_join_all_backward.assert_not_called()

    @mock.patch("shared.pipeline.JoinAllStep.backward")
    @mock.patch("shared.pipeline.JoinAllStep.forward")
    @mock.patch("shared.pipeline.SegmentationStepShared.forward")
    @mock.patch("shared.pipeline.SegmentationStepShared.backward")
    @mock.patch("shared.pipeline.OCRCorrectionStep.forward")
    @mock.patch("shared.pipeline.OCRCorrectionStep.backward")
    def test_all_options_manual(
            self,
            mock_correction_shared_forward,
            mock_correction_shared_backward,
            mock_segmentation_shared_forward,
            mock_segmentation_shared_backward,
            mock_join_all_forward,
            mock_join_all_backward,
    ):
        for mock_method in [
            mock_correction_shared_forward,
            mock_correction_shared_backward,
            mock_segmentation_shared_forward,
            mock_segmentation_shared_backward,
            mock_join_all_backward,
            mock_join_all_forward,
        ]:
            mock_method.side_effect = lambda x: x

        options = PipelineStepEnum.get_names()
        options_str = ", ".join(options)

        with open(FILENAME_IMAGE, "rb") as file:
            response = self.client.post(
                self.url,
                data={
                    "file": file,
                    "engineId": self.ocr_engine.id,
                    "source": "nl",
                    "options": options_str,
                },
                format='multipart'
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        with self.subTest("Non-empty response"):
            self.assertTrue(response.content)

        with self.subTest("Segmentation called"):
            # Should be called a few times for each option
            mock_segmentation_shared_forward.assert_called()
            mock_segmentation_shared_backward.assert_called()

        with self.subTest("Correction called"):
            # Should be called a few times for each option
            mock_correction_shared_forward.assert_called()
            mock_correction_shared_backward.assert_called()

        with self.subTest("join all called"):
            mock_join_all_forward.assert_called_once()
            mock_join_all_backward.assert_called_once()

    @mock.patch("shared.pipeline.JoinAllStep.backward")
    @mock.patch("shared.pipeline.JoinAllStep.forward")
    @mock.patch("shared.pipeline.SegmentationStep.backward")
    @mock.patch("shared.pipeline.SegmentationStep.forward")
    def test_no_options_manual(
            self,
            mock_segmentation_forward,
            mock_segmentation_backward,
            mock_join_all_forward,
            mock_join_all_backward,
    ):
        for mock_method in [
            mock_segmentation_backward,
            mock_segmentation_forward,
            mock_join_all_backward,
            mock_join_all_forward,
        ]:
            mock_method.side_effect = lambda x: x

        options_str = ""

        with open(FILENAME_IMAGE, "rb") as file:
            response = self.client.post(
                self.url,
                data={
                    "file": file,
                    "engineId": self.ocr_engine.id,
                    "source": "nl",
                    "options": options_str,
                },
                format='multipart'
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

        with open(FILENAME_IMAGE, "rb") as file:
            response = self.client.post(
                self.url,
                data={
                    "file": file,
                    "engineId": self.ocr_engine.id,
                    "source": "nl",
                    "options": options_str,
                },
                format='multipart'
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        with self.subTest("Info"):
            self.assertIn(
                "Invalid pipeline options", response.json()["error"], response.json()
            )

    def test_dont_reconstruct(self):
        with open(FILENAME_IMAGE, "rb") as file:
            response = self.client.post(
                self.url,
                data={
                    "file": file,
                    "engineId": self.ocr_engine.id,
                    "reconstruct": False,
                },
                format='multipart'
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        ocr_text = response.content.decode("utf-8")

        with self.subTest("Non-empty response"):
            self.assertTrue(ocr_text)

        with self.subTest("Correct OCR output"):
            self.assertIn("History of Automated Advisories", ocr_text)

        with self.subTest("Text content type"):
            self.assertEqual("text/plain", response["Content-Type"])

        with self.subTest("Usage"):
            # Get last usage
            usage = UsageOCR.objects.last()
            self.assertGreater(usage.image_size, 0, "Image size not set")
            self.assertEqual(usage.overlay_size, len(ocr_text))
            self.assertEqual(usage.status, StatusField.SUCCESS)
            self.assertEqual(usage.ocr_engine, self.ocr_engine)

    def test_no_api_key(self):
        # Remove authentication credentials
        self.client.credentials()
        with open(FILENAME_IMAGE, "rb") as file:
            response = self.client.post(
                self.url,
                data={"file": file, "engineId": self.ocr_engine.id},
                format='multipart'
            )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class OCRPipelineOptionsAPIViewTest(APITestCase, SharedTestAPIPermission):
    def setUp(self):
        self.url = reverse("OCR:pipeline:options")

        # Create an organisation
        self.organisation = Organisation.objects.create(name='Test Org')

        # Create an API key
        _, self.api_key = OrganisationAPIKey.objects.create_key(
            name='Test Key',
            organisation=self.organisation,
        )

        # Set the authentication credentials
        self.client.credentials(HTTP_API_KEY=self.api_key)

    def test_get_all(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        options = response.json()
        self.assertTrue(options)

        # Check response format
        self.assertIsInstance(options, list)
        for option in options:
            self.assertIsInstance(option, dict)
            self.assertIn("name", option)
            self.assertIn("description", option)

        # Check that all pipeline steps are included
        step_names = [step["name"] for step in options]
        expected_steps = [step.value.name for step in PipelineStepEnum]
        self.assertListEqual(sorted(step_names), sorted(expected_steps))

    def test_no_api_key(self):
        # Remove authentication credentials
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
