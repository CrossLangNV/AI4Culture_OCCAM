import unittest

from text_parser.sentence_extraction import extract_sentences_from_lines

EXAMPLE_TEXT = ['This is a sent-',
                    'ence. This is',
                    'another sentence.',
                    'As you can see, it',
                    'is split over multi-',
                    'ple lines.']

EXAMPLE_OUTPUT = [
    'This is a sentence.',
    'This is another sentence.',
    'As you can see, it is split over multiple lines.'
]

class MyTestCase(unittest.TestCase):
    def test_something(self):

        text_segmented = extract_sentences_from_lines(EXAMPLE_TEXT, "en")

        self.assertListEqual(text_segmented, EXAMPLE_OUTPUT, "Ideal output not obtained")


if __name__ == '__main__':
    unittest.main()
