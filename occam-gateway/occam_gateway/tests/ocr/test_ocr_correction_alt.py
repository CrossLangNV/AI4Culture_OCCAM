import unittest
from xml.etree import ElementTree as ET

from ocr.ocr_correction_alt import OCRCorrectorAlt


class TestOCRCorrectionAlt(unittest.TestCase):
    def test_basic_correction(self):
        # Sample OCR content (PageXML) with an intentional error
        ocr_content = b'''<?xml version="1.0" encoding="UTF-8"?>
    <Page xmlns="http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15">
        <TextRegion id="r1">
            <TextLine id="l1">
                <TextEquiv>
                    <Unicode>This is a smple text.</Unicode>
                </TextEquiv>
            </TextLine>
        </TextRegion>
    </Page>
    '''

        # Manual transcription content with the correct text
        manual_transcription = b"This is a sample text."

        # Initialize OCRCorrector with the sample contents
        ocr_corrector = OCRCorrectorAlt(ocr_content=ocr_content, mantrans_content=manual_transcription, log=True)
        ocr_corrector.run()

        # Get the corrected content
        corrected_content = ocr_corrector.corrected_content

        # Parse the corrected_content
        namespaces = {'pc': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15'}
        root = ET.fromstring(corrected_content)
        unicode_element = root.find('.//pc:Unicode', namespaces)
        unicode_text = unicode_element.text

        # Check if 'smple' has been corrected to '~sample'
        self.assertEqual(unicode_text, 'This is a ~sample text.')

    def test_no_correction_needed(self):
        # OCR content that matches manual transcription perfectly
        ocr_content = b'''<?xml version="1.0" encoding="UTF-8"?>
    <Page xmlns="http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15">
        <TextRegion id="r1">
            <TextLine id="l1">
                <TextEquiv>
                    <Unicode>All correct text here.</Unicode>
                </TextEquiv>
            </TextLine>
        </TextRegion>
    </Page>
    '''

        manual_transcription = b"All correct text here."

        ocr_corrector = OCRCorrectorAlt(ocr_content=ocr_content, mantrans_content=manual_transcription, log=True)
        ocr_corrector.run()

        corrected_content = ocr_corrector.corrected_content

        # Parse the corrected_content
        namespaces = {'pc': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15'}
        root = ET.fromstring(corrected_content)
        unicode_element = root.find('.//pc:Unicode', namespaces)
        unicode_text = unicode_element.text

        # Since the text is correct, there should be no correction markers
        self.assertEqual(unicode_text, 'All correct text here.')
        self.assertNotIn('~', unicode_text)

    def test_multiple_errors(self):
        # OCR content with multiple errors
        ocr_content = b'''<?xml version="1.0" encoding="UTF-8"?>
    <Page xmlns="http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15">
        <TextRegion id="r1">
            <TextLine id="l1">
                <TextEquiv>
                    <Unicode>Ths is an exmple of OCR.</Unicode>
                </TextEquiv>
            </TextLine>
        </TextRegion>
    </Page>
    '''

        manual_transcription = b"This is an example of OCR."

        ocr_corrector = OCRCorrectorAlt(ocr_content=ocr_content, mantrans_content=manual_transcription, log=True)
        ocr_corrector.run()

        corrected_content = ocr_corrector.corrected_content

        # Parse the corrected_content
        namespaces = {'pc': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15'}
        root = ET.fromstring(corrected_content)
        unicode_element = root.find('.//pc:Unicode', namespaces)
        unicode_text = unicode_element.text

        # Check that 'Ths' and 'exmple' have been corrected
        self.assertEqual(unicode_text, '~This is an ~example of OCR.')

    def test_additional_words_in_transcription(self):
        # OCR content missing words present in manual transcription
        ocr_content = b'''<?xml version="1.0" encoding="UTF-8"?>
    <Page xmlns="http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15">
        <TextRegion id="r1">
            <TextLine id="l1">
                <TextEquiv>
                    <Unicode>The quick brown fox.</Unicode>
                </TextEquiv>
            </TextLine>
        </TextRegion>
    </Page>
    '''

        manual_transcription = b"The quick brown fox jumps over the lazy dog."

        ocr_corrector = OCRCorrectorAlt(ocr_content=ocr_content, mantrans_content=manual_transcription, log=True)
        ocr_corrector.run()

        corrected_content = ocr_corrector.corrected_content

        # Parse the corrected_content
        namespaces = {'pc': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15'}
        root = ET.fromstring(corrected_content)
        unicode_element = root.find('.//pc:Unicode', namespaces)
        unicode_text = unicode_element.text

        # Expected corrected text
        expected_text = 'The quick brown fox [[jumps over the lazy dog]] .'

        # Check that the corrected text matches the expected text
        self.assertEqual(expected_text, unicode_text)

    def test_non_matching_content(self):
        # Completely different OCR content and transcription
        ocr_content = b'''<?xml version="1.0" encoding="UTF-8"?>
    <Page xmlns="http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15">
        <TextRegion id="r1">
            <TextLine id="l1">
                <TextEquiv>
                    <Unicode>Unrelated OCR content.</Unicode>
                </TextEquiv>
            </TextLine>
        </TextRegion>
    </Page>
    '''

        manual_transcription = b"Different manual transcription."

        ocr_corrector = OCRCorrectorAlt(ocr_content=ocr_content, mantrans_content=manual_transcription, log=True)
        ocr_corrector.run(similarity_threshold=0.5)  # Set the similarity threshold
        corrected_content = ocr_corrector.corrected_content

        # Parse the corrected_content
        namespaces = {'pc': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15'}
        root = ET.fromstring(corrected_content)
        unicode_element = root.find('.//pc:Unicode', namespaces)
        unicode_text = unicode_element.text

        # Expected corrected text (unchanged OCR content)
        expected_text = 'Unrelated OCR content.'

        # Check that the corrected text matches the expected text
        self.assertEqual(unicode_text, expected_text)

    def test_special_characters(self):
        # OCR content with special characters
        ocr_content = b'''<?xml version="1.0" encoding="UTF-8"?>
    <Page xmlns="http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15">
        <TextRegion id="r1">
            <TextLine id="l1">
                <TextEquiv>
                    <Unicode>Special ch@racters &amp; symbols!</Unicode>
                </TextEquiv>
            </TextLine>
        </TextRegion>
    </Page>
    '''

        manual_transcription = b"Special characters and symbols!"

        ocr_corrector = OCRCorrectorAlt(ocr_content=ocr_content, mantrans_content=manual_transcription, log=True)
        ocr_corrector.run()

        corrected_content = ocr_corrector.corrected_content

        # Parse the corrected_content
        namespaces = {'pc': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15'}
        root = ET.fromstring(corrected_content)
        unicode_element = root.find('.//pc:Unicode', namespaces)
        unicode_text = unicode_element.text

        # Expected corrected text
        expected_text = 'Special ~characters [&] ~and symbols!'

        # Check that the corrected text matches the expected text
        self.assertEqual(unicode_text, expected_text)


if __name__ == '__main__':
    unittest.main()
