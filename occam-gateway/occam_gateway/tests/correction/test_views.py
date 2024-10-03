import io
import os

import django.test
from django.urls import reverse
from rest_framework import status

from correction.models import UsageCorrection
from correction.views import (
    CorrectionEnum,
    CorrectionFileAPIView,
    CorrectionOptionsAPIView,
    PostOCRLLMAPIView,
    PostOCRSymSpellAPIView,
    PostOCRSymSpellFlairAPIView,
)
from shared.pipeline import PageXMLWrapper
from tests.organisation.utils import create_test_api_headers
from tests.shared.utils_test_views import SharedTestAPIPermission

FILENAME_XML_SMALL = os.path.join(
    os.path.dirname(__file__), "../test_data", "ocr_small.xml"
)


class PostOCRSymSpellAPIViewTest(django.test.TestCase, SharedTestAPIPermission):
    NAMESPACE = "post-OCR_correction"
    VIEWNAME = "sym_spell"

    def setUp(self) -> None:
        self.url = reverse(f"{self.NAMESPACE}:{self.VIEWNAME}")
        self.view = PostOCRSymSpellAPIView()

        # Login
        self.headers = create_test_api_headers()

    def test_post(self):
        language = "fr"
        text = "misdlen Self Indulgence, scrivent ahrègé M57 est un groupe d'étutropunt américain, onigiraire de New Yek. leur musique est formée d'un nélange de hipobop, puk rock, rock alternatif, electronia, sechno et musique isdurtrielle. le nom du greupe provient d'un alham du chonteur Sinmy Arire et de sen père enregistré en 1995."

        response = self.client.post(
            self.url,
            headers=self.headers,
            data={"text": text, "language": language},
        )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        text_corrected = response.data.get("text")

        with self.subTest("Non-empty response"):
            self.assertTrue(text_corrected)

        with self.subTest("Correct response"):
            self.assertNotEqual(text, text_corrected)


class PostOCRSymSpellFlairAPIViewTest(django.test.TestCase, SharedTestAPIPermission):
    NAMESPACE = "post-OCR_correction"
    VIEWNAME = "sym_spell_flair"

    def setUp(self) -> None:
        self.url = reverse(f"{self.NAMESPACE}:{self.VIEWNAME}")
        self.view = PostOCRSymSpellFlairAPIView()

        # Login
        self.headers = create_test_api_headers()

    def test_post(self):
        language = "en"
        text = "Beneficiary may appoint in writing a subistition fr succesor trusste, succedeing to all rights."

        response = self.client.post(
            self.url,
            headers=self.headers,
            data={"text": text, "language": language},
        )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        text_corrected = response.data.get("text")

        with self.subTest("Non-empty response"):
            self.assertTrue(text_corrected)

        with self.subTest("Correct response"):
            self.assertIn("successor", text_corrected)

    def test_language_not_supported(self):
        """
        Falls back to English engine in the API
        :return:
        """
        lang = "pl"

        response = self.client.post(
            self.url,
            headers=self.headers,
            data={"text": "test", "language": lang},
        )

        with self.subTest("Status code"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        with self.subTest("Info"):
            # self.assertIn("Language not supported", response.data)
            self.assertEqual(lang, response.data.get("language"))


class PostOCRLLMAPIViewTest(django.test.TestCase, SharedTestAPIPermission):
    NAMESPACE = "post-OCR_correction"
    VIEWNAME = "llm"

    def setUp(self) -> None:
        self.url = reverse(f"{self.NAMESPACE}:{self.VIEWNAME}")
        self.view = PostOCRLLMAPIView()

        # Login
        self.headers = create_test_api_headers()

    def test_post(self):
        language = "en"
        text = "Beneficiary may appoint in writing a subistition fr succesor trusste, succedeing to all rights."

        response = self.client.post(
            self.url,
            headers=self.headers,
            data={"text": text, "language": language},
        )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        text_corrected = response.data.get("text")

        with self.subTest("Non-empty response"):
            self.assertTrue(text_corrected)

        info = response.data.get("info")
        with self.subTest("Not failed"):
            self.assertNotIn("failed", info.lower())
            self.assertFalse(info, "There should be no info")

        with self.subTest("Correct response"):
            self.assertIn("successor", text_corrected)

    def test_custom_prompt(self):
        prompt = "Correct the following {language} text. Respond with a JSON with 'text' field.\n`{sentence}`"
        text = "Beneficiary may appoint in writing a subistition fr succesor trusste, succedeing to all rights."
        language = "en"

        # Original correction
        response = self.client.post(
            self.url,
            headers=self.headers,
            data={"text": text, "language": language},
        )

        with self.subTest("Sanity check - success"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        text_corrected_orig = response.data.get("text")

        response_prompt = self.client.post(
            self.url,
            headers=self.headers,
            data={"text": text, "language": language, "prompt": prompt},
        )

        with self.subTest("Success"):
            self.assertEqual(status.HTTP_200_OK, response_prompt.status_code)

        text_corrected_prompt = response_prompt.data.get("text")

        print("Original:", text_corrected_orig)
        print("Prompted:", text_corrected_prompt)

        with self.subTest("Prompted correction"):
            self.assertNotEqual(text_corrected_orig, text_corrected_prompt)

        info = response_prompt.data.get("info")
        with self.subTest("Not failed"):
            self.assertNotIn("failed", info.lower())
            self.assertFalse(info, "There should be no info")

        with self.subTest("Usage"):
            usage = UsageCorrection.objects.last()

            self.assertDictEqual(usage.extra, {"prompt": prompt})
            self.assertEqual(usage.source_size, len(text))
            self.assertEqual(usage.source_language, language)
            self.assertEqual(usage.corrected_size, len(text_corrected_prompt))
            self.assertEqual(usage.method, "llm")


class CorrectionFileAPIViewTest(django.test.TestCase):
    def setUp(self) -> None:
        self.url = reverse("correction:file")
        self.view = CorrectionFileAPIView()

        # Login
        self.headers = create_test_api_headers()

        self.option = CorrectionEnum.SYMSPELL_FLAIR.value.name

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

        correction_gt = [
            ["This is a sent-", "fence. This is", "another sentence."],
            [
                "As you can see, it",
                "is split over multi-",
                "ple lines.",
            ],
        ]

        with io.StringIO("\n".join(text)) as file:
            response = self.client.post(
                self.url,
                headers=self.headers,
                data={"file": file, "language": language, "option": self.option},
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        corrected_file = b"".join(response.streaming_content).decode("utf-8")

        with self.subTest("Non-empty response"):
            self.assertTrue(corrected_file)

        with self.subTest("Correct content"):
            file_gt = "\n\n".join("\n".join(paragraph) for paragraph in correction_gt)

            self.assertListEqual(file_gt.splitlines(), corrected_file.splitlines())

        with self.subTest("Usage"):
            usage = UsageSegmentation.objects.last()

            n_text = sum(map(len, text)) + len(text) - 1

            self.assertEqual(usage.source_size, n_text)
            self.assertEqual(usage.source_language, language)

            n_sentences = self.get_n_text(corrected_file)
            self.assertEqual(usage.target_size, n_sentences)

    def test_xml(self):
        language = "nl"

        correction_gt = [
            ["10"],
            [
                "Frituur Marcel",
                "BIW-kasticket",
                "lightspeed ticket nummer: 171959",
                "27/03/2024 12.53",
                "AFHALEN",
                "Laurent",
                "15924",
            ],
            # [
            #     "Naam Klem Middel hillentje Middel Bicky Burger ZONDER Frikandel Min Bamihapjes Bilterballen Kaaskroket Gaſhaalkroket Kip sate Vandel Ketchup tomaat Bioky Dressing Andalouse Americain Samoeral StoofvleesSAUS Coca Cola 330"
            # ],
            # [
            #     "1O TO RO Q C TC DO j C 1 ( 1C 2C 2 C 1C 2 O Totaal Betaling Bancontact Fotaal betaald"
            # ],
            # [
            #     "Prijs 19.20 7 60 47 5 9 O0 Z. 50 3 50 5 80 5 20 3.10 9 00 2.80 100 1 O0 2 00 2.00 1.00"
            # ],
            # ["§ 131.20 Bedrad"],
            # ["† BIN"],
            ["131.*", "Totaal"],
            # [
            #     "Netto 123// 6 123.77 BIW totaal Bedankt voor uw bezoek Frituur Marcel Ter platen 4 SOOO Sent 324 86 63 84 44 BE0764827875"
            # ],
            # ["BTW 7.43 7.43"],
            # ["13"],
            # ["1"],
            # ["Controle gs gelella Datum Counter"],
            # ["Tijdstip"],
            # ["BEShE ЕБ65."],
            # ["Signatenat aart l FlUHash lickel nmine/ Versie Produclera Device lD"],
            # [],
        ]

        with open(FILENAME_XML_SMALL, "rb") as file:
            response = self.client.post(
                self.url,
                headers=self.headers,
                data={"file": file, "language": language, "option": self.option},
            )

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        corrected_file = b"".join(response.streaming_content).decode("utf-8")

        with self.subTest("Non-empty response"):
            self.assertTrue(corrected_file)

        page_xml = PageXMLWrapper()
        with io.StringIO(corrected_file) as io_corrected_file:
            page_xml.parse(io_corrected_file)

        paragraphs_corrected = page_xml.get_paragraphs()

        with self.subTest("Correct response - number paragraphs"):
            self.assertEqual(len(correction_gt), len(paragraphs_corrected))

        for i, (paragraph_gt, paragraph) in enumerate(
            zip(correction_gt, page_xml.get_paragraphs())
        ):
            with self.subTest(f"Correct response - paragraph {i}"):
                self.assertListEqual(paragraph_gt, paragraph)

        with self.subTest("Usage"):
            usage = UsageSegmentation.objects.last()

            self.assertEqual(usage.source_size, 811)
            self.assertEqual(usage.source_language, language)

            n_sentences = self.get_n_text(text_segmented)
            # Weird empty paragraph at the end, so -1
            self.assertEqual(usage.target_size, n_sentences - 1)

    def test_all_options(self):
        options = self.client.get(
            reverse("correction:options"), headers=self.headers
        ).json()

        for option in options:
            option_name = option["name"]

            with self.subTest(f"Option: {option_name}"):
                with open(FILENAME_XML_SMALL, "rb") as file:
                    response = self.client.post(
                        self.url,
                        headers=self.headers,
                        data={"file": file, "language": "en", "option": option_name},
                    )

                self.assertEqual(status.HTTP_200_OK, response.status_code)

                corrected_file = b"".join(response.streaming_content).decode("utf-8")

                self.assertTrue(corrected_file)

                page_xml = PageXMLWrapper()
                with io.StringIO(corrected_file) as io_corrected_file:
                    page_xml.parse(io_corrected_file)

                paragraphs_corrected = page_xml.get_paragraphs()
                self.assertTrue(paragraphs_corrected)


class CorrectionOptionsAPIViewTest(django.test.TestCase, SharedTestAPIPermission):
    def setUp(self):
        self.url = reverse("correction:options")
        self.view = CorrectionOptionsAPIView()

        # Login
        self.headers = create_test_api_headers()

    def test_get_all(self):
        response = self.client.get(self.url, headers=self.headers)

        with self.subTest("Access"):
            self.assertEqual(status.HTTP_200_OK, response.status_code)

        options = response.json()

        with self.subTest("Non-empty response"):
            self.assertTrue(options)

        representation: list[dict] = []
        for step in [
            CorrectionEnum.SYMSPELL,
            CorrectionEnum.SYMSPELL_FLAIR,
            CorrectionEnum.LLM,
        ]:
            info = step.value
            representation.append(
                {
                    "name": info.name,
                    "description": info.description,
                }
            )

        self.assertListEqual(representation, options)
