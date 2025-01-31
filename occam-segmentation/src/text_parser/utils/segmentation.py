import warnings
from typing import List, Union, Optional

from sentence_splitter import split_text_into_sentences


class TextSegmenter:
    """
    Class for splitting text into sentences using the Moses sentence splitter.

    Attributes:
        text (str): The text to be split into sentences.
        language (str, Optional): The language of the text. Default is `None`..
    """

    SUPPORTED_LANGUAGES = [
        "da",
        "cs",
        "nl",
        "en",
        "fi",
        "fr",
        "de",
        "el",
        "hu",
        "it",
        "lv",
        "lt",
        "pl",
        "pt",
        "ro",
        "sk",
        "sl",
        "es",
        "sv",
        "ru",
        "ca",
        "is",
        "no",
        "tr",
    ]

    def __init__(self, text: str, language: Union[str, None] = None):
        """
        Initialize the TextSegmenter instance.

        Args:
            text (str): The text to be split in sentences.
            language (str, Optional): The language of the text. Default is `None`.
        """
        self.text = text
        self.language = language

    def segment(self) -> List[str]:
        """
        Split the text into sentences using the Moses sentence splitter.

        Returns:
            List[str]: A list of sentences.
        """
        # segment text using moses sentence splitter

        language_moses = self.get_moses_language(self.language)

        sentences = split_text_into_sentences(text=self.text, language=language_moses)

        # skip empty sentences
        sentences = [sentence for sentence in sentences if sentence.strip()]

        return sentences

    def get_moses_language(self, language: Optional[str]) -> str:
        default_language = "en"

        if language is None:
            return default_language

        language = language.lower()

        if language in self.SUPPORTED_LANGUAGES:
            return language
        elif language == "bg":
            warnings.warn(
                f"Language '{self.language}' not supported by sentence splitter, falling back to "
                "ru for sentence splitting.",
                Warning,
            )
            return "ru"
        else:
            warnings.warn(
                f"Language '{self.language}' not supported by sentence splitter, falling back to "
                "en for sentence splitting.",
                Warning,
            )

        return default_language
