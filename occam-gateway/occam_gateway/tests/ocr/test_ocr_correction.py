import unittest
from unittest.mock import patch

from ocr.ocr_correction import OCRCorrector


class TestOCRCorrection(unittest.TestCase):

    @patch('ocr.ocr_correction.LineBasedTextFile.read')
    @patch('ocr.ocr_correction.PageXMLOutput.read_lines')
    @patch('ocr.ocr_correction.PageXMLOutput.update_lines')
    def test_basic_correction(self, mock_update_lines, mock_read_lines, mock_read):
        # Mocking file reads and XML reads
        mock_read_lines.return_value = ["This is a smple text."]
        mock_read.return_value = ["This is a sample text."]

        # Mock OCR and manual transcription contents
        ocr_corrector = OCRCorrector(ocrfilename="mock_ocr.xml", mantransfilename="mock_mantrans.txt", log=True)
        ocr_corrector.run(ocrupdatefile="mock_output.xml")

        # Check that 'smple' has been corrected to 'sample' with correction markers
        corrected_line = ocr_corrector.correctedwords
        self.assertIn('~sample', corrected_line)

    @patch('ocr.ocr_correction.LineBasedTextFile.read')
    @patch('ocr.ocr_correction.PageXMLOutput.read_lines')
    @patch('ocr.ocr_correction.PageXMLOutput.update_lines')
    def test_no_correction_needed(self, mock_update_lines, mock_read_lines, mock_read):
        # OCR content that matches manual transcription perfectly
        mock_read_lines.return_value = ["All correct text here."]
        mock_read.return_value = ["All correct text here."]

        ocr_corrector = OCRCorrector(ocrfilename="mock_ocr.xml", mantransfilename="mock_mantrans.txt", log=True)
        ocr_corrector.run(ocrupdatefile="mock_output.xml")

        corrected_line = ocr_corrector.correctedwords
        self.assertEqual("All correct text here.", " ".join(corrected_line))
        self.assertNotIn('~', " ".join(corrected_line))

    @patch('ocr.ocr_correction.LineBasedTextFile.read')
    @patch('ocr.ocr_correction.PageXMLOutput.read_lines')
    @patch('ocr.ocr_correction.PageXMLOutput.update_lines')
    def test_multiple_errors(self, mock_update_lines, mock_read_lines, mock_read):
        # OCR content with multiple errors
        mock_read_lines.return_value = ["Ths is an exmple of OCR."]
        mock_read.return_value = ["This is an example of OCR."]

        ocr_corrector = OCRCorrector(ocrfilename="mock_ocr.xml", mantransfilename="mock_mantrans.txt", log=True)
        ocr_corrector.run(ocrupdatefile="mock_output.xml")

        corrected_line = ocr_corrector.correctedwords
        self.assertIn('~This', corrected_line)
        self.assertIn('~example', corrected_line)

    @patch('ocr.ocr_correction.LineBasedTextFile.read')
    @patch('ocr.ocr_correction.PageXMLOutput.read_lines')
    @patch('ocr.ocr_correction.PageXMLOutput.update_lines')
    def test_additional_words_in_transcription(self, mock_update_lines, mock_read_lines, mock_read):
        # OCR content missing words present in manual transcription
        mock_read_lines.return_value = ["The quick brown fox."]
        mock_read.return_value = ["The quick brown fox jumps over the lazy dog."]

        ocr_corrector = OCRCorrector(ocrfilename="mock_ocr.xml",
                                     mantransfilename="mock_mantrans.txt",
                                     log=True)
        ocr_corrector.run(ocrupdatefile="mock_output.xml")

        corrected_line = ocr_corrector.correctedwords
        self.assertIn('[[jumps over the lazy dog]]', corrected_line)

    @patch('ocr.ocr_correction.LineBasedTextFile.read')
    @patch('ocr.ocr_correction.PageXMLOutput.read_lines')
    @patch('ocr.ocr_correction.PageXMLOutput.update_lines')
    def test_non_matching_content(self, mock_update_lines, mock_read_lines, mock_read):
        # Completely different OCR content and transcription
        mock_read_lines.return_value = ["Unrelated OCR content. This shouldn't match with anything."]
        mock_read.return_value = ["Different manual transcription."]

        ocr_corrector = OCRCorrector(ocrfilename="mock_ocr.xml", mantransfilename="mock_mantrans.txt", log=True)
        ocr_corrector.run(ocrupdatefile="mock_output.xml", addorig=False)

        corrected_line = ocr_corrector.correctedwords
        self.assertEqual("Unrelated OCR content.", " ".join(corrected_line))

    @patch('ocr.ocr_correction.LineBasedTextFile.read')
    @patch('ocr.ocr_correction.PageXMLOutput.read_lines')
    @patch('ocr.ocr_correction.PageXMLOutput.update_lines')
    def test_special_characters(self, mock_update_lines, mock_read_lines, mock_read):
        # OCR content with special characters
        mock_read_lines.return_value = ["Special ch@racters & symbols!"]
        mock_read.return_value = ["Special characters and symbols!"]

        ocr_corrector = OCRCorrector(ocrfilename="mock_ocr.xml", mantransfilename="mock_mantrans.txt", log=True)
        ocr_corrector.run(ocrupdatefile="mock_output.xml")

        corrected_line = ocr_corrector.correctedwords
        self.assertIn('~characters', corrected_line)
        self.assertIn('[&]', corrected_line)
        self.assertIn('~and', corrected_line)


if __name__ == '__main__':
    unittest.main()
