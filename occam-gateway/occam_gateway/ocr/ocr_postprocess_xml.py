from lxml import etree


def add_custom_reading_order(xml_content):
    """
    Add 'custom="readingOrder {index:i}"' to the TextRegion and TextLine elements in the given PageXML content,
    while handling namespaces dynamically.
    """
    # Parse the XML content with lxml
    root = etree.fromstring(xml_content.encode('utf-8'))

    # Extract the namespace dynamically from the root tag
    nsmap = {'ns': root.nsmap[None]}  # Default namespace

    # Find all TextRegion elements and update their "custom" attribute
    text_regions = root.findall('.//ns:TextRegion', namespaces=nsmap)
    for region_index, text_region in enumerate(text_regions):
        # Update the TextRegion custom attribute
        text_region.set('custom', f'readingOrder {{index:{region_index}}}')

        # Find all TextLine elements inside the TextRegion
        text_lines = text_region.findall('.//ns:TextLine', namespaces=nsmap)
        for line_index, text_line in enumerate(text_lines):
            # Update the TextLine custom attribute
            text_line.set('custom', f'readingOrder {{index:{line_index}}}')

    # Return the modified XML as a string
    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='utf-8').decode('utf-8')
