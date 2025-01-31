import os

from django.core.files.base import File
from rest_framework.test import APIClient
from rest_framework.test import APITestCase

from pero_ocr_app.models import ImageFile, LayoutModel, OCRModel

ROOT_BACKEND = os.path.join(os.path.dirname(__file__), '..')
MEDIA = os.path.join(ROOT_BACKEND, 'media')
FILENAME_IMAGE = os.path.join(MEDIA, 'image3.jpg')
FILENAME_LAYOUT_MODEL = os.path.join(MEDIA, 'layout_model.zip')
FILENAME_OCR_MODEL = os.path.join(MEDIA, 'ocr_model.zip')

client = APIClient()

URL_OCR = '/ocr/'


class TestFoo(APITestCase):
    """ Test module for GET all documents API """

    def setUp(self):
        # Upload image, layout model, and ocr model

        with open(FILENAME_IMAGE, 'rb') as f:
            obj = ImageFile.objects.create(title='Example image')
            obj.image.save(FILENAME_IMAGE, File(f))

        with open(FILENAME_LAYOUT_MODEL, 'rb') as f:
            obj = LayoutModel.objects.create(title='Example layout model')
            obj.layout_model.save(FILENAME_LAYOUT_MODEL, File(f))

        with open(FILENAME_OCR_MODEL, 'rb') as f:
            obj = OCRModel.objects.create(title='Example OCR model')
            obj.ocr_model.save(FILENAME_OCR_MODEL, File(f))

        if 1:
            print(ImageFile.objects.all())
            print(LayoutModel.objects.all())
            print(OCRModel.objects.all())

        pass

    def test_foo(self):
        # get API response

        data = {'image_file': ImageFile.objects.all()[0].pk,
                'layout_model': LayoutModel.objects.all()[0].pk,
                'ocr_model': OCRModel.objects.all()[0].pk}

        response = self.client.post(URL_OCR,
                                    data=data)

        print(response.content)

        self.assertEqual(0, 1)
