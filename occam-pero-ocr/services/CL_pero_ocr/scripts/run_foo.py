import argparse
import configparser
import os

from pero_ocr.document_ocr.layout import PageLayout
from pero_ocr.document_ocr.page_parser import PageParser

from configs.parser import configuration_pero_ocr
from src.dump import get_image, image_folder_name, layout_model_name, get_engine, \
    ocr_model_name, get_page_layout_text


ROOT = os.path.join(os.path.dirname(__file__), '..')

def get_args():
    """
    method for parsing of arguments for PERO-OCR: OCR an image script
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("-f", "--filename", help="Input filename to read the image.")
    parser.add_argument("-x", "--xml", help="Output filename to save the xml to.")
    parser.add_argument("-t", "--txt", help="Output filename to save the text to.")

    args = parser.parse_args()

    return args


def main(filename,
         filename_xml,
         filename_txt):
    with open(filename, 'rb') as f_image:
        img = get_image(f_image.read())

    id = os.path.split(filename)[-1]

    if 1:
        config = configuration_pero_ocr(image_folder_name, layout_model_name, ocr_model_name)
        config_path= None
    elif 1:
        # test_layout_model + test_ocr_model
        config = configparser.ConfigParser()
        config_path = os.path.join(ROOT, 'configs/config_test.ini')
        config.read(config_path)
    else:
        config = configparser.ConfigParser()
        config_path = os.path.join(ROOT, 'configs/config_eu_cz_printed_newspapers_2010.ini')
        config.read(config_path)

    page_parser = PageParser(config,
                             #config_path=config_path # TODO make work with the relative paths from the config.
                             )

    page_layout = PageLayout(id=id,
                             page_size=img.shape[:2],
                             )

    page_layout = page_parser.process_page(img, page_layout)

    page_layout.to_pagexml(filename_xml)

    text = get_page_layout_text(page_layout)
    with open(filename_txt, 'w', encoding='utf-8') as out_f:
        out_f.write(text)

    return {'xml': page_layout.to_pagexml_string(),
            'txt': text}


if __name__ == '__main__':
    args = get_args()

    filename = args.filename
    filename_xml = args.xml
    filename_txt = args.txt

    main(filename,
         filename_xml,
         filename_txt
         )
