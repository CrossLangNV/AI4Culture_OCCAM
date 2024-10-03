import unittest
from lxml import etree
import difflib

from ocr.ocr_postprocess_xml import add_custom_reading_order


class TestAddCustomReadingOrder(unittest.TestCase):

    def normalize_xml(self, xml_str):
        """ Parse and canonicalize the XML string to ignore formatting and namespace prefix differences """
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.XML(xml_str.encode('utf-8'), parser)
        # Return canonical XML (removes extraneous whitespace and normalizes the structure)
        return etree.tostring(root, pretty_print=True).decode('utf-8')

    def show_diff(self, original_xml, modified_xml):
        """Show diff between the original XML and modified XML"""
        diff = difflib.unified_diff(
            original_xml.splitlines(),
            modified_xml.splitlines(),
            lineterm='',
            fromfile='Original XML',
            tofile='Modified XML'
        )
        return '\n'.join(diff)

    def test_add_custom_reading_order(self):
        # Sample XML input with multiple TextRegions and TextLines (before custom attributes are added)
        sample_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <PcGts xmlns="http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15 http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15/pagecontent.xsd">
            <Page imageFilename="orig.jpg" imageWidth="1646" imageHeight="1069">
                <TextRegion id="tr_1">
                    <TextLine id="tl_1">
                        <TextEquiv>
                            <Unicode>Example Text 1</Unicode>
                        </TextEquiv>
                    </TextLine>
                    <TextLine id="tl_2">
                        <TextEquiv>
                            <Unicode>Example Text 2</Unicode>
                        </TextEquiv>
                    </TextLine>
                </TextRegion>
                <TextRegion id="tr_2">
                    <TextLine id="tl_3">
                        <TextEquiv>
                            <Unicode>Example Text 3</Unicode>
                        </TextEquiv>
                    </TextLine>
                    <TextLine id="tl_4">
                        <TextEquiv>
                            <Unicode>Example Text 4</Unicode>
                        </TextEquiv>
                    </TextLine>
                </TextRegion>
            </Page>
        </PcGts>
        '''

        # Running the function to modify the XML (adding custom attributes)
        result = add_custom_reading_order(sample_xml)

        # Pretty print for better visualization in the test output
        print("Modified XML Output:")
        print(result)

        # Show the differences between the original XML and modified XML
        print("\nDifferences between original and modified XML:")
        original_xml = self.normalize_xml(sample_xml)
        modified_xml = self.normalize_xml(result)
        print(self.show_diff(original_xml, modified_xml))

        # Expected output after applying the transformation (for validation)
        expected_output = '''<?xml version="1.0" ?>
        <PcGts xmlns="http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15 http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15/pagecontent.xsd">
          <Page imageFilename="orig.jpg" imageWidth="1646" imageHeight="1069">
            <TextRegion id="tr_1" custom="readingOrder {index:0}">
              <TextLine id="tl_1" custom="readingOrder {index:0}">
                <TextEquiv>
                  <Unicode>Example Text 1</Unicode>
                </TextEquiv>
              </TextLine>
              <TextLine id="tl_2" custom="readingOrder {index:1}">
                <TextEquiv>
                  <Unicode>Example Text 2</Unicode>
                </TextEquiv>
              </TextLine>
            </TextRegion>
            <TextRegion id="tr_2" custom="readingOrder {index:1}">
              <TextLine id="tl_3" custom="readingOrder {index:0}">
                <TextEquiv>
                  <Unicode>Example Text 3</Unicode>
                </TextEquiv>
              </TextLine>
              <TextLine id="tl_4" custom="readingOrder {index:1}">
                <TextEquiv>
                  <Unicode>Example Text 4</Unicode>
                </TextEquiv>
              </TextLine>
            </TextRegion>
          </Page>
        </PcGts>
        '''

        # Normalize and compare the expected and modified XML structures
        self.assertEqual(self.normalize_xml(result), self.normalize_xml(expected_output))


# Run the tests
if __name__ == '__main__':
    unittest.main()
