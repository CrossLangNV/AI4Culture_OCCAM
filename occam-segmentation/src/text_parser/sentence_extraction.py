from .utils.concatenation import concatenate_text_lines
from .utils.models import Text
from .utils.segmentation import TextSegmenter


def extract_sentences_from_lines(text: list[str], language) -> list[str]:
    """
    This method extracts individual sentences from a list of text lines,
    employing line concatenation and sentence segmentation.
    :param text: a list of sentences/text lines
    :param language: language code of the text.
        E.g. "en" for English, "de" for German, "fr" for French, etc.
        useful for algorithms that use language-specific rules
    :return:
         a list of automatically segmented sentences
    """

    text = Text(text)

    # Sentence joiner
    text_concatenated = concatenate_text_lines(
        text, delimiter=" ", fix_hyphenation=True, filter_sentences=True
    )

    text = TextSegmenter(text_concatenated, language).segment()

    return text
