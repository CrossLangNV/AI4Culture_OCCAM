from rest_framework import serializers


class SegmentationSerializer(serializers.Serializer):
    text = serializers.ListField(child=serializers.CharField(), required=True)
    language = serializers.CharField()


class SegmentationFileSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
    language = serializers.CharField()


class SegmentationFileResponseSerializer(serializers.Serializer):
    text = serializers.ListField(
        child=serializers.ListField(child=serializers.CharField(), required=True)
    )
    file = serializers.CharField(required=False)
    language = serializers.CharField(required=False, allow_null=True, allow_blank=False)
