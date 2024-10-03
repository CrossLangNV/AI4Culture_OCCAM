import os
import unittest
import warnings

from lxml import etree

from shared.pipeline import (
    JoinAllStep,
    OCRCorrectionSymSpellFlairStep,
    PageXMLParagraphParser,
    PageXMLWrapper,
    Paragraph,
    SegmentationStep,
    Text,
    TextParagraphParser,
    TranslationStep,
    translate_pipeline,
)

FILENAME_TEXT = r"test.txt"
FILENAME_OCR = r"ocr.xml"
FILENAME_OCR_GT = r"ocr_gt.xml"
FILENAME_OCR_CORRECTED = r"ocr_corrected.xml"

DIR_DATA = os.path.join(os.path.dirname(__file__), "../test_data")
FILENAME_TEXT = os.path.join(DIR_DATA, FILENAME_TEXT)
FILENAME_OCR = os.path.join(DIR_DATA, FILENAME_OCR)
FILENAME_OCR_GT = os.path.join(DIR_DATA, FILENAME_OCR_GT)
FILENAME_OCR_CORRECTED = os.path.join(DIR_DATA, FILENAME_OCR_CORRECTED)

for filename in [FILENAME_TEXT, FILENAME_OCR, FILENAME_OCR_GT, FILENAME_OCR_CORRECTED]:
    if not os.path.exists(filename):
        warnings.warn(f"File {filename} does not exist for testing OCR")


class TestPageXMLWrapper(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def test_parse_pagexml(self):
        page_xml = PageXMLWrapper()
        page_xml.parse(FILENAME_OCR)

        with self.subTest("Paragraphs"):
            self.assertEqual(17, len(page_xml.get_paragraphs()), "Number of paragraphs")

        for i, (n_lines, paragraphs) in enumerate(
            zip([1, 7], page_xml.get_paragraphs())
        ):
            with self.subTest(f"Paragraph {i}"):
                self.assertEqual(n_lines, len(paragraphs), "Number of sentences")

    def test_parse_corrected_xml(self):
        """
        Test the parsing of the corrected xml
        Bug 15/05/2024
        :return:
        """

        page_xml = PageXMLWrapper()
        page_xml.parse(FILENAME_OCR_CORRECTED)

        with self.subTest("Paragraphs"):
            self.assertEqual(2, len(page_xml.get_paragraphs()), "Number of paragraphs")

        for i, (n_lines, paragraphs) in enumerate(
            zip([21, 22], page_xml.get_paragraphs())
        ):
            with self.subTest(f"Paragraph {i}"):
                self.assertEqual(n_lines, len(paragraphs), "Number of sentences")


class PageXMLParagraphParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.page_xml = PageXMLWrapper()
        self.page_xml.parse(FILENAME_OCR)

        self.paragraphs = [
            ["10"],
            [
                "Frituur Marcel",
                "BIW-kasticket",
                "Lightspeed ticket nummer: 171959",
                "27/03/2024 12.53",
                "AFHALEN",
                "Laurent",
                "15924",
            ],
        ]

        self.step = PageXMLParagraphParser()

        self.maxDiff = None

    def test_forward(self):
        paragraphs = self.step.forward(self.page_xml)

        with self.subTest("paragraph 0"):
            self.assertListEqual(self.paragraphs[0], paragraphs[0])

        with self.subTest("paragraph 1"):
            self.assertListEqual(
                self.paragraphs[1],
                paragraphs[1],
            )

    def test_backward(self):
        self.step.set_state(self.page_xml)

        paragraphs_upper = [[s.upper() for s in p] for p in self.paragraphs]
        page_xml_restored = self.step.backward(paragraphs_upper)

        with self.subTest("Changed state"):
            self.assertNotEqual(
                str(self.page_xml),
                str(page_xml_restored),
                "The original page seems to be altered",
            )

        # Check if the text is in the page xml
        for i, (paragraph_in, paragraph_new) in enumerate(
            zip(paragraphs_upper, page_xml_restored.get_paragraphs())
        ):
            with self.subTest(f"paragraph {i}"):
                self.assertListEqual(paragraph_in, paragraph_new)

    def test_forward_backward(self):
        paragraphs = self.step.forward(self.page_xml)
        page_xml_restored = self.step.backward(paragraphs)

        self.assertEqual(str(self.page_xml), str(page_xml_restored))

    def test_forward_backward_k(self, k=10):
        x = self.page_xml

        for i in range(k):
            y = self.step.forward(x)
            x = self.step.backward(y)

        self.assertEqual(str(self.page_xml), str(x))

    def test_forward_backward_corrected(self):
        page_xml = PageXMLWrapper().parse(FILENAME_OCR_CORRECTED)
        paragraphs = self.step.forward(page_xml)
        page_xml_restored = self.step.backward(paragraphs)

        self.assertEqual(str(page_xml), str(page_xml_restored))


class TextParagraphParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.step = TextParagraphParser()

        with open(FILENAME_TEXT, "r") as f:
            self.text = f.read()

        self.paragraphs = Text(
            [
                Paragraph(["This is some example text.", "Or is it?"]),
                Paragraph(
                    [
                        "(I needed an empty line to separate the two blocks of text)",
                        "this is the end",
                    ]
                ),
            ]
        )

    def test_forward(self):
        paragraphs = self.step.forward(self.text)

        for i, (paragraph_gt, paragraph) in enumerate(zip(self.paragraphs, paragraphs)):
            with self.subTest(f"Paragraph {i}"):
                self.assertListEqual(paragraph_gt, paragraph)

    def test_backward(self):
        paragraphs_upper = Text(
            [Paragraph([s.upper() for s in p]) for p in self.paragraphs]
        )
        text_restored = self.step.backward(paragraphs_upper)

        with self.subTest("Changed state"):
            self.assertNotEqual(
                str(self.text),
                str(text_restored),
                "The original page seems to be altered",
            )

        for i, (line_gt, line) in enumerate(
            zip(self.text.split("\n"), text_restored.split("\n"))
        ):
            with self.subTest(f"Line {i}"):
                self.assertEqual(line_gt.upper(), line)

    def test_forward_backward(self):
        paragraphs = self.step.forward(self.text)
        text_restored = self.step.backward(paragraphs)

        self.assertEqual(self.text, text_restored)

    def test_forward_backward_k(self, k=10):
        x = self.text

        for i in range(k):
            y = self.step.forward(x)
            x = self.step.backward(y)

        self.assertEqual(str(self.text), str(x))


class OCRCorrectionStepTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = Text(
            [
                Paragraph(
                    [
                        "Avviso",
                        "Avendo nicevuto ordine del comando dupiumo",
                        "dei inTervenire a pranzo di guerrà la",
                        "Classe del 1886 al 1841 Sei riformaza",
                        "s quelle delle casse del 1826 1783-94-94",
                        "prossimamenta",
                        "Zistino Viverii.",
                    ],
                ),
                Paragraph(
                    [
                        "di mongia se si può ma senzo reclumare",
                        "Obiei Sa 309 con contorno di 200 prolunzat",
                        "Bombe a mano in gran quantita con contorni",
                        "dii gelatina exposiva. Carta al rugo col",
                        "contorno du schegge di gradate, Ordinarie.",
                    ]
                ),
            ]
        )

        self.text_gt = Text(
            [
                Paragraph(
                    [
                        "Avviso",
                        "Avendo ricevuto ordine del comando dupiumo",
                        "dei inTervenire a pranzo di guerre la",
                        "Classe del 1886 al 1841 Sei riformata",
                        "s quelle delle casse del 1826 1783-94-94",
                        "prossimamenta",
                        "Listino Viversi.",
                    ]
                ),
                Paragraph(
                    [
                        "di mangia se si può ma senza reclamare",
                        "Obici Sa 309 con contorno di 200 prolungati",
                        "Bombe a mano in gran quantità con contorni",
                        "dii gelatina esplosiva. Carta al rigo col",
                        "contorno du schegge di graduate, Ordinarie.",
                    ]
                ),
            ]
        )

        self.source_lang = "it"

        self.step = OCRCorrectionSymSpellFlairStep(
            source_lang=self.source_lang,
        )

    def test_forward(self):
        y = self.step.forward(self.text)

        with self.subTest("Same dimensions - paragraphs"):
            self.assertEqual(len(self.text), len(y))

        for i, (paragraph_gt, paragraph_corrected) in enumerate(zip(self.text_gt, y)):
            with self.subTest(f"Paragraph {i}"):
                self.assertListEqual(paragraph_gt, paragraph_corrected)

    def test_backward(self):
        text_reconstructed = self.step.backward(self.text_gt)

        with self.subTest("Same dimensions - paragraphs"):
            for i, (paragraph_gt, paragraph_reconstructed) in enumerate(
                zip(self.text, text_reconstructed)
            ):
                self.assertEqual(
                    len(paragraph_gt), len(paragraph_reconstructed), f"Paragraph {i}"
                )

        with self.subTest("Identity function"):
            for paragraph_gt, paragraph_reconstructed in zip(
                self.text_gt, text_reconstructed
            ):
                self.assertListEqual(paragraph_gt, paragraph_reconstructed)

    def test_forward_backward(self):
        y = self.step.forward(self.text)
        x = self.step.backward(y)

        for i, (paragraph_gt, paragraph_corrected) in enumerate(zip(self.text_gt, x)):
            with self.subTest(f"Paragraph {i}"):
                self.assertListEqual(paragraph_gt, paragraph_corrected)

    def test_forward_backward_k(self, k=2):
        """
        After passing once, the text should be the same
        :param k:
        :return:
        """
        y_inter = self.step.forward(self.text)
        x_inter = self.step.backward(y_inter)

        x = x_inter
        for i in range(k):
            y = self.step.forward(x)
            x = self.step.backward(y)

        for i, (paragraph_gt, paragraph_reconstructed) in enumerate(zip(x_inter, x)):
            with self.subTest(f"Paragraph {i}"):
                self.assertListEqual(paragraph_gt, paragraph_reconstructed)


class SegmentationStepTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = Text(
            [
                Paragraph(["A single", "sentence. And an-", "other one."]),
                Paragraph(
                    [
                        "Another paragraph.",
                        "With two sentences",
                        'or more? "Yes, more."',
                        "And the last one.",
                    ]
                ),
            ]
        )

        self.text_segmented_gt = Text(
            [
                Paragraph(["A single sentence.", "And another one."]),
                Paragraph(
                    [
                        "Another paragraph.",
                        "With two sentences or more?",
                        '"Yes, more."',
                        "And the last one.",
                    ]
                ),
            ]
        )
        self.source_lang = "en"

        self.step = SegmentationStep(
            source_lang=self.source_lang,
        )

    def test_forward(self):
        y = self.step.forward(self.text)

        with self.subTest("Same dimensions - paragraphs"):
            self.assertEqual(len(self.text), len(y))

        for i, (paragraph_gt, paragraph_segmented) in enumerate(
            zip(self.text_segmented_gt, y)
        ):
            with self.subTest(f"Paragraph {i}"):
                self.assertListEqual(paragraph_gt, paragraph_segmented)

    def test_backward(self):
        # Set the state
        _ = self.step.forward(self.text)

        text_reconstructed = self.step.backward(self.text_segmented_gt)

        with self.subTest("Same dimensions - paragraphs"):
            for i, (paragraph_gt, paragraph_reconstructed) in enumerate(
                zip(self.text, text_reconstructed)
            ):
                self.assertEqual(
                    len(paragraph_gt), len(paragraph_reconstructed), f"Paragraph {i}"
                )

        with self.subTest("Concatenation - paragraph 0"):
            self.assertEqual(
                "sentence. And another",
                text_reconstructed[0][1],
                "Paragraph 0 - sentence 1",
            )
            self.assertEqual(
                "one.", text_reconstructed[0][2], "Paragraph 0 - sentence 2"
            )

        with self.subTest("No de-hyphenation - paragraph 1"):
            for i, (sentence_gt, sentence_reconstructed) in enumerate(
                zip(self.text[1], text_reconstructed[1])
            ):
                self.assertEqual(
                    sentence_gt, sentence_reconstructed, f"Paragraph 1 - sentence {i}"
                )

    def test_forward_backward_forward(self):
        y_inter = self.step.forward(self.text)
        x = self.step.backward(y_inter)
        y_redo = self.step.forward(x)

        for i, (paragraph_inter, paragraph_redo) in enumerate(zip(y_inter, y_redo)):
            with self.subTest(f"Paragraph {i}"):
                self.assertListEqual(paragraph_inter, paragraph_redo)

    def test_forward_backward_k(self, k=5):
        """
        After passing once, the text should be the same
        :param k:
        :return:
        """
        y_inter = self.step.forward(self.text)
        x_inter = self.step.backward(y_inter)

        x = x_inter
        for i in range(k):
            y = self.step.forward(x)
            x = self.step.backward(y)

        for i, (paragraph_gt, paragraph_reconstructed) in enumerate(zip(x_inter, x)):
            with self.subTest(f"Paragraph {i}"):
                self.assertListEqual(paragraph_gt, paragraph_reconstructed)


class JoinAllStepTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = Text(
            [
                Paragraph(["A single", "sentence. And an-", "other one."]),
                Paragraph(
                    [
                        "Another paragraph.",
                        "With two sentences",
                        'or more? "Yes, more."',
                        "And the last one.",
                    ]
                ),
            ]
        )

        self.text_joined = (
            "A single sentence. And an- other one. "
            "Another paragraph. With two sentences or more? "
            '"Yes, more." And the last one.'
        )

        self.step = JoinAllStep(
            source_lang="zh",
        )

    def test_forward(self):
        y = self.step.forward(self.text)

        with self.subTest("Single paragraph, single sentence"):
            self.assertEqual(1, len(y), "Number of paragraphs")
            self.assertEqual(1, len(y[0]), "Number of sentences")

        with self.subTest("Ground truth"):
            self.assertEqual(self.text_joined, y[0][0])

    def test_backward(self):
        # Set the state
        _ = self.step.forward(self.text)

        text_reconstructed = self.step.backward(Text([Paragraph([self.text_joined])]))

        with self.subTest("Same dimensions - paragraphs"):
            for i, (paragraph, paragraph_reconstructed) in enumerate(
                zip(self.text, text_reconstructed)
            ):
                self.assertEqual(
                    len(paragraph), len(paragraph_reconstructed), f"Paragraph {i}"
                )

        with self.subTest("Same content"):
            for i, (paragraph, paragraph_reconstructed) in enumerate(
                zip(self.text, text_reconstructed)
            ):
                for j, (sentence, sentence_reconstructed) in enumerate(
                    zip(paragraph, paragraph_reconstructed)
                ):
                    self.assertEqual(
                        sentence,
                        sentence_reconstructed,
                        f"Paragraph {i} - sentence {j}",
                    )

    def test_forward_backward(self):
        y_inter = self.step.forward(self.text)
        x = self.step.backward(y_inter)
        y_redo = self.step.forward(x)

        for i, (paragraph_inter, paragraph_redo) in enumerate(zip(y_inter, y_redo)):
            with self.subTest(f"Paragraph {i}"):
                self.assertListEqual(paragraph_inter, paragraph_redo)

    def test_forward_backward_k(self, k=5):
        """
        After passing once, the text should be the same
        :param k:
        :return:
        """
        y_inter = self.step.forward(self.text)
        x_inter = self.step.backward(y_inter)

        x = x_inter
        for i in range(k):
            y = self.step.forward(x)
            x = self.step.backward(y)

        for i, (paragraph_gt, paragraph_reconstructed) in enumerate(zip(x_inter, x)):
            with self.subTest(f"Paragraph {i}"):
                self.assertListEqual(paragraph_gt, paragraph_reconstructed)


class TranslationStepTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = Text([Paragraph(["A single sentence."])])
        self.source_lang = "en"
        self.target_lang = "nl"

        self.step = TranslationStep(
            source_lang=self.source_lang, target_lang=self.target_lang
        )

    def test_forward(self):
        text_translated = self.step.forward(self.text)

        with self.subTest("Same dimensions - paragraphs"):
            self.assertEqual(len(self.text), len(text_translated))

        with self.subTest("Same dimensions - sentences"):
            for i, (paragraph, paragraph_translated) in enumerate(
                zip(self.text, text_translated)
            ):
                self.assertEqual(
                    len(paragraph), len(paragraph_translated), f"Paragraph {i}"
                )

        with self.subTest("Translation"):
            sentence_0_0_translated = text_translated[0][0]

            print(sentence_0_0_translated)
            self.assertNotEqual("A single sentence.", sentence_0_0_translated)

    def test_forward_big(self):
        text = Text(
            [
                Paragraph(["A single sentence.", "Another sentence."]),
                Paragraph(["? What another sentence? :o"]),
            ]
        )

        text_translated = self.step.forward(text)

        with self.subTest("Same dimensions - paragraphs"):
            self.assertEqual(len(text), len(text_translated))

        with self.subTest("Same dimensions - sentences"):
            for i, (paragraph, paragraph_translated) in enumerate(
                zip(text, text_translated)
            ):
                self.assertEqual(
                    len(paragraph), len(paragraph_translated), f"Paragraph {i}"
                )

        l_translations = [t for paragraph in text_translated for t in paragraph]

        with self.subTest("Different outputs"):
            self.assertEqual(len(l_translations), len(set(l_translations)))

        with self.subTest("Text line cleaning"):
            for sentence_translation in l_translations:
                self.assertNotIn("\n", sentence_translation, "Newline in translation")
                self.assertEqual(
                    sentence_translation.strip(),
                    sentence_translation,
                    "Leading or trailing whitespace",
                )

    def test_backward(self):
        """
        The backward function shouldn't do anything
        :return:
        """
        foobar = "foobar"

        self.assertEqual(foobar, self.step.backward(foobar), "Identity function")


class TranslatePipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = etree.parse(FILENAME_OCR)

        self.page_xml = PageXMLWrapper()
        self.page_xml.parse(FILENAME_OCR)

        self.source_lang = "nl"

    def test_call(self):
        page_xml_translated = translate_pipeline(
            self.page_xml, source_lang=self.source_lang, target_lang="en"
        )

        orig_term = "tomaat".lower()
        translated_term = "tomato".lower()

        # "naam" -> "name"
        with self.subTest(f"Sanity check - '{orig_term}'"):
            self.assertIn(orig_term, str(self.page_xml).lower())

        with self.subTest(f"Translation - '{translated_term}'"):
            self.assertIn(translated_term, str(page_xml_translated).lower())

        if 0:
            # export to file
            page_xml_translated.write(
                "ocr_test_translated.xml", encoding="utf-8", pretty_print=True
            )
