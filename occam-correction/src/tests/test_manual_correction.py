import os
import unittest

from src.post_ocr_correction.manual_correction.correct import LineBasedTextFile, PageXMLOutput, NgramDict, \
    NgramMatch, OCRCorrector


class TestLineBasedTextFile(unittest.TestCase):
    def setUp(self):
        self.filename = "test.txt"
        with open(self.filename, 'w') as f:
            f.write("This is a test file.\nIt has multiple lines.\n")

    def tearDown(self):
        os.remove(self.filename)

    def test_read(self):
        lbtf = LineBasedTextFile(self.filename)
        lines = lbtf.read()
        self.assertEqual(lines, ["This is a test file.", "It has multiple lines."])

    def test_write(self):
        lbtf = LineBasedTextFile(self.filename)
        lines = ["Line 1", "Line 2"]
        lbtf.write(lines)
        with open(self.filename, 'r') as f:
            content = f.read().strip().split('\n')
        self.assertEqual(content, lines)


class TestPageXMLOutput(unittest.TestCase):
    def setUp(self):
        self.xml_content = '''<root>
            <TextRegion>
                <TextLine>
                    <Word>
                        <Unicode>Test line 1</Unicode>
                    </Word>
                </TextLine>
                <TextLine>
                    <Word>
                        <Unicode>Test line 2</Unicode>
                    </Word>
                </TextLine>
            </TextRegion>
        </root>'''
        self.filename = "test.xml"
        with open(self.filename, 'w') as f:
            f.write(self.xml_content)

    def tearDown(self):
        os.remove(self.filename)

    def test_read_lines(self):
        pxo = PageXMLOutput(self.filename)
        lines = pxo.read_lines()
        self.assertEqual(lines, ["Test line 1", "Test line 2"])


class TestNgramDict(unittest.TestCase):
    def setUp(self):
        self.words = ["this", "is", "a", "test"]
        self.ngram_dict = NgramDict(self.words, ngramlen=2)

    def test_extract_ngrams(self):
        expected_ngrams = {
            'this is': [0],
            'is a': [1],
            'a test': [2]
        }
        self.assertEqual(self.ngram_dict.ngrams, expected_ngrams)

    def test_get_closest_ngrams(self):
        closest_ngrams = self.ngram_dict.get_closest_ngrams('this is')
        self.assertIn('this is', closest_ngrams)


class TestNgramMatch(unittest.TestCase):
    def test_initialization(self):
        match = NgramMatch('ocrngram', 0, 'manngram', 1, 1)
        self.assertEqual(match.ocrngram, 'ocrngram')
        self.assertEqual(match.ocrpos, 0)
        self.assertEqual(match.manngram, 'manngram')
        self.assertEqual(match.manpos, 1)
        self.assertEqual(match.distance, 1)


class TestOCRCorrector(unittest.TestCase):
    def setUp(self):
        self.ocr_filename = "ocr_test.xml"
        self.mantrans_filename = "mantrans_test.txt"
        self.output_filename = "output_test.xml"

        # Simplified XML structure for the test case
        with open(self.ocr_filename, 'w') as f:
            f.write('''<root>
                            <TextRegion>
                                <TextLine>
                                    <Coords points="0,0 0,100 100,100 100,0"/>
                                    <Word>
                                        <Unicode>This</Unicode>
                                        <Unicode>is</Unicode>
                                        <Unicode>a</Unicode>
                                        <Unicode>tst</Unicode>
                                    </Word>
                                </TextLine>
                            </TextRegion>
                        </root>''')
        # Simplified manual transcription for the test case
        with open(self.mantrans_filename, 'w') as f:
            f.write("This is a test")

    def tearDown(self):
        os.remove(self.ocr_filename)
        os.remove(self.mantrans_filename)
        if os.path.exists(self.output_filename):
            os.remove(self.output_filename)

    def test_ocr_correction(self):
        # Create OCRCorrector instance
        corrector = OCRCorrector(self.ocr_filename, self.mantrans_filename, ngramlen=3, log=True)

        # Run the correction process
        corrector.run(self.output_filename)

        corrected_lines = corrector.correctedwords

        # Check that the correction was applied
        corrected_text = " ".join(corrected_lines).replace("~", "")
        self.assertIn("This is a test", corrected_text)


if __name__ == "__main__":
    unittest.main()
