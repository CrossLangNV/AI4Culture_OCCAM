import unittest

from text_parser.utils.concatenation import concatenate_text_lines

EXAMPLE_TEXT = [
    "This is a sent-",
    "ence. This is",
    "another sentence.",
    "As you can see, it",
    "is split over multi-",
    "ple lines.",
]


# tests for concatenate_text_lines
class TestConcatenateTextLines(unittest.TestCase):
    def test_concatenation_with_defaults(self, text=None):
        if text is None:
            text = EXAMPLE_TEXT
        concatenated_text = concatenate_text_lines(text)

        # Assert that the returned text is a string
        assert isinstance(concatenated_text, str)

    def test_concatenation_with_fix_hyphenation(self, text=None):
        if text is None:
            text = EXAMPLE_TEXT
        concatenated_text = concatenate_text_lines(text)

        # Assert that the returned text is a string
        assert isinstance(concatenated_text, str)

        # Assert that hyphenated words have been concatenated (i.e. New-York -> NewYork)
        assert "-" not in concatenated_text
