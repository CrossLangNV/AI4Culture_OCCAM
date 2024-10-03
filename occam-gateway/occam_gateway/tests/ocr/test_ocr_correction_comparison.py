import unittest
from xml.etree import ElementTree as ET

from ocr.ocr_correction_alt import OCRCorrectorAlt, PageXMLOutputAlt
from ocr.ocr_correction import OCRCorrector


class TestOCRCorrectorComparison(unittest.TestCase):

    def setUp(self):
        # Load test data files
        with open('../test_data/test_diary_ocr_manual_correction.txt', 'rb') as mantrans_file:
            self.mantrans_content = mantrans_file.read()

        with open('../test_data/test_diary_ocr.xml', 'rb') as ocr_file:
            self.ocr_content = ocr_file.read()

    def test_comparison_of_corrections(self):
        # Initialize OCRCorrector
        ocr_corrector_new = OCRCorrectorAlt(ocr_content=self.ocr_content, mantrans_content=self.mantrans_content, log=True)
        ocr_corrector_new.run()

        # Extract the lines from the corrected content
        page_output = PageXMLOutputAlt(ocr_corrector_new.corrected_content, log=True)
        extracted_lines = page_output.read_lines()

        print("Extracted Lines from New OCRCorrector:")
        for line in extracted_lines:
            print(line)

        # Parse the corrected content for OCRCorrector
        namespaces = {'pc': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15'}
        corrected_content_new = ocr_corrector_new.corrected_content
        root_new = ET.fromstring(corrected_content_new)
        unicode_element_new = root_new.find('.//pc:Unicode', namespaces)

        if unicode_element_new is None:
            print("Debug: Could not find Unicode element in the corrected content.")
            print(ET.tostring(root_new, encoding='unicode'))
            self.fail("Unicode element is missing in the corrected XML output.")

        unicode_text_new = unicode_element_new.text
        print("New OCRCorrector Output:")
        print(unicode_text_new)
        print("=" * 50)

        # Initialize OCRCorrectorOld
        ocr_corrector_old = OCRCorrector(ocrfilename='../test_data/03.xml', mantransfilename='../test_data/03.txt', log=True)
        ocr_corrector_old.run(ocrupdatefile="mock_output.xml")

        # Get the corrected content from OCRCorrectorOld
        corrected_content_old = ocr_corrector_old.correctedwords
        corrected_text_old = " ".join(corrected_content_old)
        print("Old OCRCorrectorOld Output:")
        print(corrected_text_old)
        print("=" * 50)

        # The comparison part is left as is for now, since you want to manually inspect the outputs
        self.assertNotEqual(unicode_text_new, corrected_text_old)  # This is just to prevent the test from passing


if __name__ == '__main__':
    unittest.main()
