import io
import os

import django.test
from django.urls import reverse
from rest_framework import status

from segmentation.models import UsageSegmentation
from segmentation.views import SegmentationPipelineAPIView, SegmentationFileAPIView
from shared.pipeline import Text
from ..organisation.utils import create_test_api_headers
from ..shared.utils_test_views import SharedTestAPIPermission

FILENAME_XML = os.path.join(os.path.dirname(__file__), "../test_data", "ocr.xml")


class SegmentationPipelineAPIViewTest(django.test.TestCase, SharedTestAPIPermission):
    NAMESPACE = "segmentation"
    VIEWNAME = "pipeline"

    def setUp(self) -> None:
        self.url = reverse(f"{self.NAMESPACE}:{self.VIEWNAME}")
        self.view = SegmentationPipelineAPIView()

        # Login
        self.headers = create_test_api_headers()

    def test_post(self):
        text = [
            "This is a sent-",
            "ence. This is",
            "another sentence.",
            "As you can see, it",
            "is split over multi-",
            "ple lines.",
        ]
        language = "en"

        sentences = [
            "This is a sentence.",
            "This is another sentence.",
            "As you can see, it is split over multiple lines.",
        ]

        response = self.client.post(
            self.url,
            headers=self.headers,
            data={"text": text, "language": language},
            content_type="application/json",
        )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code, response.data)

        text_segmented = response.data.get("text")

        with self.subTest("Non-empty response"):
            self.assertTrue(text_segmented)

        with self.subTest("Correct response"):
            self.assertListEqual(sentences, text_segmented)

        with self.subTest("Usage"):
            usage = UsageSegmentation.objects.last()

            self.assertEqual(usage.source_size, sum(map(len, text)))
            self.assertEqual(usage.source_language, language)
            self.assertEqual(usage.target_size, sum(map(len, text_segmented)))


class SegmentationFileAPIViewTest(django.test.TestCase, SharedTestAPIPermission):
    NAMESPACE = "segmentation"
    VIEWNAME = "file"

    def setUp(self) -> None:
        self.url = reverse(f"{self.NAMESPACE}:{self.VIEWNAME}")
        self.view = SegmentationFileAPIView()

        # Login
        self.headers = create_test_api_headers()

    def test_text(self):
        text = [
            "This is a sent-",
            "ence. This is",
            "another sentence.",
            "",
            "As you can see, it",
            "is split over multi-",
            "ple lines.",
        ]

        language = "en"

        sentences_gt = [
            ["This is a sentence.", "This is another sentence."],
            [
                "As you can see, it is split over multiple lines.",
            ],
        ]

        with io.StringIO("\n".join(text)) as file:
            response = self.client.post(
                self.url,
                headers=self.headers,
                data={"file": file, "language": language},
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code, response.data)

        text_segmented = response.data.get("text")

        with self.subTest("Non-empty response"):
            self.assertTrue(text_segmented)

        with self.subTest("Correct response"):
            for i, (paragraph_gt, paragraph) in enumerate(
                zip(sentences_gt, text_segmented)
            ):
                self.assertListEqual(paragraph_gt, paragraph, f"Paragraph {i}")

        with self.subTest("File response"):
            file_segmented = response.data.get("file")
            file_gt = "\n\n".join("\n".join(paragraph) for paragraph in sentences_gt)

            self.assertEqual(file_gt, file_segmented)

        with self.subTest("Usage"):
            usage = UsageSegmentation.objects.last()

            n_text = sum(map(len, text)) + len(text) - 1

            self.assertEqual(usage.source_size, n_text)
            self.assertEqual(usage.source_language, language)

            n_sentences = self.get_n_text(text_segmented)
            self.assertEqual(usage.target_size, n_sentences)

    def test_xml(self):
        language = "en"

        sentences = [
            ["10"],
            [
                "Frituur Marcel BIW-kasticket Lightspeed ticket nummer: 171959 27/03/2024 12.53 AFHALEN Laurent 15924"
            ],
            [
                "Naam Klem Middel hillentje Middel Bicky Burger ZONDER Frikandel Min Bamihapjes Bilterballen Kaaskroket Gaſhaalkroket Kip sate Vandel Ketchup tomaat Bioky Dressing Andalouse Americain Samoeral StoofvleesSAUS Coca Cola 330"
            ],
            [
                "1O TO RO Q C TC DO j C 1 ( 1C 2C 2 C 1C 2 O Totaal Betaling Bancontact Fotaal betaald"
            ],
            [
                "Prijs 19.20 7 60 47 5 9 O0 Z. 50 3 50 5 80 5 20 3.10 9 00 2.80 100 1 O0 2 00 2.00 1.00"
            ],
            ["§ 131.20 Bedrad"],
            ["† BIN"],
            ["131.* Totaal"],
            [
                "Netto 123// 6 123.77 BIW totaal Bedankt voor uw bezoek Frituur Marcel Ter platen 4 SOOO Sent 324 86 63 84 44 BE0764827875"
            ],
            ["BTW 7.43 7.43"],
            ["13"],
            ["1"],
            ["Controle gs gelella Datum Counter"],
            ["Tijdstip"],
            ["BEShE ЕБ65."],
            ["Signatenat aart l FlUHash lickel nmine/ Versie Produclera Device lD"],
            [],
        ]

        with open(FILENAME_XML, "rb") as file:
            response = self.client.post(
                self.url,
                headers=self.headers,
                data={"file": file, "language": language},
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code, response.data)

        text_segmented = response.data.get("text")

        with self.subTest("Non-empty response"):
            self.assertTrue(text_segmented)

        with self.subTest("Correct response"):
            self.assertListEqual(sentences, text_segmented)

        with self.subTest("Usage"):
            usage = UsageSegmentation.objects.last()

            self.assertEqual(usage.source_size, 811)
            self.assertEqual(usage.source_language, language)

            n_sentences = self.get_n_text(text_segmented)
            # Weird empty paragraph at the end, so -1
            self.assertEqual(usage.target_size, n_sentences - 1)

    def get_n_text(self, text: Text):
        return sum(
            [sum([len(line) for line in par]) + len(par) - 1 for par in text]
        ) + 2 * (len(text) - 1)
