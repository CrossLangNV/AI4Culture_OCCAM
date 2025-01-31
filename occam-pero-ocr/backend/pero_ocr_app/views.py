import os
import sys

from django.conf import settings
from rest_framework import generics
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ImageFile, ImageFolder, LayoutModel, OCRModel, OCRImage, OCRFolder
from .serializers import ImageFileSerializer, ImageFolderSerializer, LayoutModelSerializer, OCRModelSerializer, \
    OCRImageSerializer, OCRFolderSerializer

sys.path.append(os.path.join(settings.BASE_DIR, "pero_ocr_app/pero-ocr/"))

from pero_ocr_app.ocr_models.ocr import OCRViewShared


class ImageFileUploadView(generics.ListCreateAPIView):
    parser_class = (FileUploadParser,)

    serializer_class = ImageFileSerializer
    queryset = ImageFile.objects.all()


class ImageFileUploadDetailView(generics.RetrieveUpdateDestroyAPIView):
    parser_class = (FileUploadParser,)

    serializer_class = ImageFileSerializer
    queryset = ImageFile.objects.all()


class ImageFolderUploadView(generics.ListCreateAPIView):
    serializer_class = ImageFolderSerializer
    queryset = ImageFolder.objects.all()


class ImageFolderUploadDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ImageFolderSerializer
    queryset = ImageFolder.objects.all()


class LayoutModelUploadView(generics.ListCreateAPIView):
    serializer_class = LayoutModelSerializer
    queryset = LayoutModel.objects.all()


class LayoutModelUploadDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LayoutModelSerializer
    queryset = LayoutModel.objects.all()


class OCRModelUploadView(generics.ListCreateAPIView):
    serializer_class = OCRModelSerializer
    queryset = OCRModel.objects.all()


class OCRModelUploadDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OCRModelSerializer
    queryset = OCRModel.objects.all()


class OCRView(generics.CreateAPIView,
              OCRViewShared):
    serializer_class = OCRImageSerializer
    queryset = OCRImage.objects.all()

    def post(self, request, *args, **kwargs):
        self.check_post_input(request)

        # 0) Init models &
        # Configuration of pero_ocr

        self.set_config(request)

        # 1) Init of data
        filename = self.init_data(request)

        return_data = self.process_image_filename(filename)

        return Response(return_data)

    def init_data(self, request):
        key = 'image_file' if 1 else 'id_image'

        id_image = request.data.get(key, None)

        image_file = ImageFile.objects.get(pk=id_image)
        filename = str(image_file.image)

        return filename


class OCRFolderView(generics.CreateAPIView,
                    OCRViewShared):
    serializer_class = OCRFolderSerializer
    queryset = OCRFolder.objects.all()

    def post(self, request, *args, **kwargs):

        self.check_post_input(request)

        # 0) Init models &
        # Configuration of pero_ocr

        self.set_config(request)

        # 1) init data

        filenames_to_process = self.init_data(request)

        return_data = {}

        for filename in filenames_to_process:
            return_data_i = self.process_image_filename(filename)

            return_data.update(return_data_i)

        return Response(return_data)

    def init_data(self, request):

        key = 'image_folder' if 1 else "id_folder"

        image_folder = self._get_model(request, ImageFolder, key)

        image_folder_filename = str(image_folder.folder)

        # unzip image_folder:
        basename = self._unzipper(image_folder_filename)

        # 2) load the image

        folder_path = os.path.join(self.get_folder_image(), basename)

        print(f'Reading images from {folder_path}.')

        # Give back unzipped folder + filename.
        filenames_to_process = [os.path.join(basename, f) for f in os.listdir(folder_path) if
                                os.path.splitext(f)[1].lower() in ['.jpg', '.jpeg', '.png', '.tif', '.tiff']
                                ]

        if filenames_to_process is None:
            raise Exception(f"No images in {folder_path}. Supported formats: .jpg, .jpeg, .png, .tif")

        return filenames_to_process


# testing
class IndexPageView(APIView):
    def get(self, request):
        return_data = {
            "error": "0",
            "message": "Successful",
        }
        return Response(return_data)
