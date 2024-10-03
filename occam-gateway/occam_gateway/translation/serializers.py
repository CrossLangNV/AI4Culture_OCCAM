from rest_framework import serializers

from shared.pipeline import PipelineStepEnum


class SharedSerializer(serializers.Serializer):
    source = serializers.CharField(
        help_text="The source language code", max_length=10, required=True
    )
    target = serializers.CharField(
        help_text="The target language code", max_length=10, required=True
    )


class TranslateSnippetSerializer(SharedSerializer):
    snippet = serializers.CharField(required=True, help_text="The text to translate")


class TranslateFileSerializer(SharedSerializer):
    file = serializers.FileField(required=True, help_text="The file to translate")


class CommaSeparatedListField(serializers.Field):
    """
    Custom field to handle comma-separated list inputs.
    Converts a comma-separated string into a list of strings.
    """

    def to_representation(self, value):
        """
        Serialize the list as a comma-separated string.
        """
        if isinstance(value, list):
            return ','.join(value)
        return value

    def to_internal_value(self, data):
        """
        Deserialize the comma-separated string into a list.
        """
        if isinstance(data, str):
            # Split by comma and strip whitespace
            data = [item.strip().upper() for item in data.split(',') if item.strip()]
            return data
        elif isinstance(data, list):
            # Ensure all items are strings
            if not all(isinstance(item, str) for item in data):
                raise serializers.ValidationError("All options must be strings.")
            return [item.strip().upper() for item in data if item.strip()]
        else:
            raise serializers.ValidationError(
                "Invalid format for options. Must be a comma-separated string or a list of strings.")


class TranslatePipelineSerializer(serializers.Serializer):
    file = serializers.FileField(
        required=True, help_text="The file to translate. Either txt or PageXML."
    )
    source = serializers.CharField(
        help_text="The source language code", max_length=10, required=True
    )
    target = serializers.CharField(
        help_text="The target language code", max_length=10, required=True
    )

    options = CommaSeparatedListField(
        help_text=(
            "A list of pipeline option keys. "
            "Available options are: DEHYPHENATION, JOIN_PARAGRAPH, SENTENCE_SEGMENTATION, "
            "CORRECTION_SYMSPELL, CORRECTION_SYMSPELL_FLAIR, CORRECTION_LLM, JOIN_PAGE, RENDER_TXT."
        ),
        required=False,
        default=[]
    )

    def validate_options(self, value):
        """
        Validate that all provided options are valid pipeline steps.
        """
        valid_keys = [step.name for step in PipelineStepEnum]
        invalid_keys = [key for key in value if key not in valid_keys]
        if invalid_keys:
            raise serializers.ValidationError([f"Invalid option key: {key}" for key in invalid_keys])
        return value


class CombinedTranslateFileSerializer(serializers.Serializer):
    file = serializers.FileField(
        required=True, help_text="The file to translate. Either txt or PageXML."
    )
    source = serializers.CharField(
        help_text="The source language code", max_length=10, required=True
    )
    target = serializers.CharField(
        help_text="The target language code", max_length=10, required=True
    )

    options = CommaSeparatedListField(
        help_text=(
            "A list of pipeline option keys. "
            "Available options are: DEHYPHENATION, JOIN_PARAGRAPH, SENTENCE_SEGMENTATION, "
            "CORRECTION_SYMSPELL, CORRECTION_SYMSPELL_FLAIR, CORRECTION_LLM, JOIN_PAGE, RENDER_TXT."
        ),
        required=False,
        default=[]
    )

    async_param = serializers.BooleanField(
        help_text="Whether to run the pipeline asynchronously.",
        required=False,
        default=False
    )

    def validate_options(self, value):
        """
        Validate that all provided options are valid pipeline steps.
        """
        valid_keys = [step.name for step in PipelineStepEnum]
        invalid_keys = [key for key in value if key not in valid_keys]
        if invalid_keys:
            raise serializers.ValidationError([f"Invalid option key: {key}" for key in invalid_keys])
        return value


class CombinedTranslateBatchSerializer(serializers.Serializer):
    file = serializers.FileField(
        required=True, help_text="ZIP file containing files to translate. Either txt or PageXML."
    )
    source = serializers.CharField(
        help_text="The source language code", max_length=10, required=True
    )
    target = serializers.CharField(
        help_text="The target language code", max_length=10, required=True
    )

    options = CommaSeparatedListField(
        help_text=(
            "A list of pipeline option keys. "
            "Available options are: DEHYPHENATION, JOIN_PARAGRAPH, SENTENCE_SEGMENTATION, "
            "CORRECTION_SYMSPELL, CORRECTION_SYMSPELL_FLAIR, CORRECTION_LLM, JOIN_PAGE, RENDER_TXT."
        ),
        required=False,
        default=[]
    )

    async_param = serializers.BooleanField(
        help_text="Whether to run the pipeline asynchronously.",
        required=False,
        default=False
    )

    def validate_options(self, value):
        """
        Validate that all provided options are valid pipeline steps.
        """
        valid_keys = [step.name for step in PipelineStepEnum]
        invalid_keys = [key for key in value if key not in valid_keys]
        if invalid_keys:
            raise serializers.ValidationError([f"Invalid option key: {key}" for key in invalid_keys])
        return value


class CombinedTranslateSnippetSerializer(serializers.Serializer):
    snippet = serializers.CharField(required=True, help_text="The text to translate")
    source = serializers.CharField(
        help_text="The source language code", max_length=10, required=True
    )
    target = serializers.CharField(
        help_text="The target language code", max_length=10, required=True
    )

    options = CommaSeparatedListField(
        help_text=(
            "A list of pipeline option keys. "
            "Available options are: DEHYPHENATION, JOIN_PARAGRAPH, SENTENCE_SEGMENTATION."
        ),
        required=False,
        default=[]
    )

    def validate_options(self, value):
        """
        Validate that all provided options are valid pipeline steps.
        """
        valid_keys = [step.name for step in PipelineStepEnum]
        invalid_keys = [key for key in value if key not in valid_keys]
        if invalid_keys:
            raise serializers.ValidationError([f"Invalid option key: {key}" for key in invalid_keys])
        return value