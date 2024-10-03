from rest_framework import serializers


class OCREvalSerializer(serializers.Serializer):
    file_ocr = serializers.FileField(help_text="OCR file. ALTO, PAGE or text")
    file_gt = serializers.FileField(help_text="Ground truth file. ALTO, PAGE or text")


class OCREvalTextSerializer(serializers.Serializer):
    text_ocr = serializers.CharField(help_text="OCR text")
    text_gt = serializers.CharField(help_text="Ground truth text")
