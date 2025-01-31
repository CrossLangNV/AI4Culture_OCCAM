import numpy as np
import cv2
from pero_ocr.document_ocr.page_parser import PageParser

layout_model_name = 'test_layout_model'
ocr_model_name = 'test_ocr_model'
image_folder_name = '' # TODO?
# image_folder_name = os.path.join(ROOT, 'output_dir')

def get_image(contents):
    """

    :param contents: file contents: file.read()
    :return:
    """

    nparr = np.fromstring(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if len(img.shape) == 2:
        img = np.stack([img, img, img], axis=2)

    return img


def get_engine(config, *args, **kwargs):
    # TODO

    page_parser = PageParser(config)

    return page_parser, None, None


def get_page_layout_text(page_layout):
    text = ""
    for line in page_layout.lines_iterator():
        text += "{}\n".format(line.transcription)
    return text
