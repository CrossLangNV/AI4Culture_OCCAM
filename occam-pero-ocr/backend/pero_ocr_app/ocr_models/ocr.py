import os
import sys

import cv2
import zipfile

from ..models import ImageFile, ImageFolder, LayoutModel, OCRModel
from .configuration import configuration_pero_ocr
from django.conf import settings

sys.path.append(os.path.join(settings.BASE_DIR, "pero_ocr_app/pero-ocr/"))
from pero_ocr.document_ocr.layout import PageLayout
from pero_ocr.document_ocr.page_parser import PageParser


class OCRViewShared(object):
    """
    Abstract class for OCRView and OCRFolderView
    """

    def check_post_input(self, request):
        for a in self.serializer_class().data:
            assert a in request.data, f'expected {a} in Request: {request.data}'

    def set_config(self, request):

        layout_model_name = self.layout_model(request)
        ocr_model_name = self.ocr_model(request)

        self.config = configuration_pero_ocr('', layout_model_name, ocr_model_name)

        os.makedirs(self.get_folder_xml(), exist_ok=True)
        os.makedirs(self.get_folder_render(), exist_ok=True)

        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # suppress tensorflow warnings on loading models

    def layout_model(self, request, *args, **kwargs):

        key = 'layout_model' if 1 else 'id_layout_model'

        layout_model_file = self._get_model(request, LayoutModel, key)

        layout_model_name = str(layout_model_file.layout_model)

        # unzip layout_model:
        layout_model_name = self._unzipper(layout_model_name)

        return layout_model_name

    def ocr_model(self, request, *args, **kwargs):

        key = 'ocr_model' if 1 else 'id_ocr_model'

        ocr_model_file = self._get_model(request, OCRModel, key)
        ocr_model_name = str(ocr_model_file.ocr_model)

        # unzip ocr model:
        ocr_model_name = self._unzipper(ocr_model_name)

        return ocr_model_name

    def get_config(self):
        try:
            return self.config
        except NameError as e:
            raise NameError("Are you sure set_config() is already called?")

    def load_image(self, filepath):

        image = cv2.imread(filepath, 1)
        if image is None:
            raise Exception(f'Unable to read image "{filepath}"')

        return image

    def process_image_filename(self, filename):

        # Load image
        image_filepath = os.path.join(self.get_folder_image(), filename)

        image_basename = os.path.splitext(os.path.basename(filename))[0]
        file_basename = os.path.splitext(filename)[0]

        image = self.load_image(image_filepath)

        # Process image
        # 3) Layout analysis + OCR

        page_layout = self.process_image(image, image_basename)

        # 4) Output page-xml and jpg. Return json containing page-xml file.

        # file_basename such that possible subfolder structures are included
        image, page_xml_string = self.save_output(image, page_layout, file_basename)

        if 0:
            # Old format:
            return_data = {
                'filename': os.path.join(self.get_folder_image(), filename),
                'page_xml': page_xml_string,
            }
        else:
            # According to API:
            return_data = {filename:
                           page_xml_string,
                           }

        return return_data

    def process_image(self, image, image_basename):

        # 3) Layout analysis + OCR

        # Init PageLayout info
        page_layout = PageLayout(id=image_basename, page_size=image.shape[:2])

        page_parser = PageParser(self.get_config())
        page_layout = page_parser.process_page(image, page_layout)

        return page_layout

    def save_output(self, image, page_layout, image_basename):
        """

        Image wordt overschreven!
        :param image:
        :param page_layout:
        :param image_basename:
        :return:
        """

        def ensure_dir(filepath):
            directory = os.path.dirname(filepath)
            os.makedirs(directory, exist_ok=True)  # Make folder if it doesn't exist yet.

        # Make subfolders if necessary

        filepath_xml = os.path.join(self.get_folder_xml(), image_basename + '.xml')
        filepath_render = os.path.join(self.get_folder_render(), image_basename + '.jpg')

        ensure_dir(filepath_xml)
        ensure_dir(filepath_render)

        # 4) Output page-xml and jpg. Return json containing page-xml file.

        page_layout.to_pagexml(filepath_xml)
        page_xml_string = page_layout.to_pagexml_string()

        # Overwrites image
        page_layout.render_to_image(image)
        cv2.imwrite(filepath_render, image,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 70])

        return image, page_xml_string

    def get_folder_image(self):

        return self.get_config()['PARSE_FOLDER']['INPUT_IMAGE_PATH']

    def get_folder_xml(self):

        return self.get_config()['PARSE_FOLDER']['OUTPUT_XML_PATH']

    def get_folder_render(self):

        return self.get_config()['PARSE_FOLDER']['OUTPUT_RENDER_PATH']

    def _get_model(self, request, model, id_name):

        assert id_name in request.data, f'no {id_name} in {request.data}'

        id_model = request.data.get(id_name, None)

        try:
            model_file = model.objects.get(pk=id_model)
        except Exception as e:
            raise Exception(e,
                            f"\nCan't find {id_name} {id_model} in {model.objects}")

        return model_file

    def _unzipper(self, zip_filename):
        """
        General shared unzipper.
        Converts zip to folder and returns the folder name.

        returns dirname

        :zip_filename: filename of .zip
        """

        unzip_dirname, ext = os.path.splitext(zip_filename)

        # assert ext == '.zip', f'extension is expected to be .zip: {ext}'

        unzip_dir = os.path.join(settings.MEDIA_ROOT, unzip_dirname)
        os.makedirs(unzip_dir, exist_ok=True)  # Make folder if it doesn't exist yet.

        # Do you want to unzip it everytime? Unless you delete it afterwards
        # If there is a change in the zip, you should update it anyways, so might indeed be the safest like this.
        with zipfile.ZipFile(os.path.join(settings.MEDIA_ROOT, zip_filename), "r") as zip_ref:
            zip_ref.extractall(unzip_dir)

        return unzip_dirname
