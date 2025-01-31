from rest_framework import serializers


class PostOCRCorrectionSerializer(serializers.Serializer):
    text = serializers.CharField(required=True)
    language = serializers.CharField()
    async_param = serializers.BooleanField(required=False, default=False)


class PostOCRCorrectionLLMSerializer(PostOCRCorrectionSerializer):
    prompt = serializers.CharField(required=False)


class CorrectionFileSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
    language = serializers.CharField()
    async_param = serializers.BooleanField(required=False, default=False)
    option = serializers.CharField(
        required=True,
    )


class ManualCorrectionStringSerializer(serializers.Serializer):
    ocr = serializers.CharField(required=True)
    transcription = serializers.CharField(required=True)

    ngram_len = serializers.IntegerField(required=False, default=3)
    max_dist_prop = serializers.FloatField(required=False, default=0.5)
    max_dist_word = serializers.IntegerField(required=False, default=5)
    min_word_sim = serializers.FloatField(required=False, default=0.5)
    min_word_sim_strong = serializers.FloatField(required=False, default=0.6)
    max_ngram_multi = serializers.IntegerField(required=False, default=3)
    max_dist_unlinked = serializers.IntegerField(required=False, default=3)
    xml_log_changes = serializers.BooleanField(required=False, default=False)
    async_param = serializers.BooleanField(required=False, default=False)


class ManualCorrectionSerializer(serializers.Serializer):
    ocr_file = serializers.FileField(required=True)
    transcription_file = serializers.FileField(required=True)

    ngram_len = serializers.IntegerField(required=False)
    max_dist_prop = serializers.FloatField(required=False)
    max_dist_word = serializers.IntegerField(required=False)
    min_word_sim = serializers.FloatField(required=False)
    min_word_sim_strong = serializers.FloatField(required=False)
    max_ngram_multi = serializers.IntegerField(required=False)
    max_dist_unlinked = serializers.IntegerField(required=False)
    xml_log_changes = serializers.BooleanField(required=False)
    async_param = serializers.BooleanField(required=False, default=False)


class CorrectionOptionsResponseSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    description = serializers.CharField(required=False)
