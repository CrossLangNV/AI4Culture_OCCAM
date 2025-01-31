from okapi_segmentation.main import okapi_segmentation
from text_parser.utils.concatenation import hyphenation_fix, concatenate_text_lines
from .general import Option


class JoinTextLines(Option):
    _name = "join_lines"
    _description = "Join text lines into a single text"

    def __init__(self):
        method = lambda text_lines: [
            concatenate_text_lines(text_lines, delimiter=" ", fix_hyphenation=False)
        ]
        super().__init__(method)


class Dehypenation(Option):
    _name = "dehyphenation"
    _description = "Fix hyphenation of words split over multiple lines"

    def __init__(self, method=hyphenation_fix):
        super().__init__(method)


class SentenceSegmentationOkapi(Option):
    _name = "sentence_segmentation/okapi"
    _description = "Extract individual sentences from text lines. Using Okapi sentence segmentation."

    def __init__(self, method=okapi_segmentation):
        super().__init__(method)
