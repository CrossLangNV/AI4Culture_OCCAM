# -*- coding: utf-8 -*-
from rest_framework import serializers
from .models import ImageFile, ImageFolder, LayoutModel, OCRModel, OCRImage, OCRFolder


class ImageFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageFile
        fields = ('id', 'title', 'image')


class ImageFolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageFolder
        fields = ('id', 'title', 'folder')


class LayoutModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = LayoutModel
        fields = ('id', 'title', 'layout_model')


class OCRModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = OCRModel
        fields = ('id', 'title', 'ocr_model')


class OCRImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OCRImage
        fields = ('image_file',
                  'layout_model',
                  'ocr_model'
                  )


class OCRFolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = OCRFolder
        fields = ('image_folder',
                  'layout_model',
                  'ocr_model'
                  )
