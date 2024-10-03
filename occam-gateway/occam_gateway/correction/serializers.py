from rest_framework import serializers


class PostOCRCorrectionSerializer(serializers.Serializer):
    text = serializers.CharField(required=True)
    language = serializers.CharField()


class PostOCRCorrectionLLMSerializer(PostOCRCorrectionSerializer):
    prompt = serializers.CharField(required=False)


class CorrectionFileSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
    language = serializers.CharField()

    option = serializers.CharField(
        required=True,
    )


class ManualCorrectionSerializer(serializers.Serializer):
    ocr_file = serializers.FileField(required=True)
    transcription_file = serializers.FileField(required=True)


class CorrectionOptionsResponseSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    description = serializers.CharField(required=False)
