import io

from ocr.pagexml import lxml_text_region_iterator, lxml_text_region_iterator_trans


def main(filename, b_rectangle=False, target=None):
    """
    filename: Can be path to page XML or file object.
    target: (Optional) language code of translated language (for multilingual page xml).
    """
    if target is not None:
        l = lxml_text_region_iterator_trans(filename, target=target, ignorewordregions=True)
    else:
        l = lxml_text_region_iterator(filename, ignorewordregions=True)

    d = {"type": "FeatureCollection", "features": []}

    for co, text_textline in l:
        feature = {
            "type": "Feature",
        }

        # Geometry
        if b_rectangle:
            h0, w0, h1, w1 = co.h0, co.w0, co.h1, co.w1

            feature["geometry"] = {"type": "Rectangle", "coordinates": [h0, w0, h1, w1]}
        else:
            feature["geometry"] = {
                "type": "Polygon",
                "coordinates": [(h, w) for (w, h) in co.l_co],
            }

        feature["properties"] = {"name": text_textline}

        d.get("features").append(feature)

    return d


def main_from_xml_string(s: str, *args, **kwargs) -> dict:
    """
    xml as string (as retrieved from the API)
    """
    # Use BytesIO and encode the string to bytes
    with io.BytesIO(s.encode('utf-8')) as f:
        return main(f, *args, **kwargs)
