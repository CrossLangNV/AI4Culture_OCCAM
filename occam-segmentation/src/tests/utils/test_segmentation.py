import unittest
from text_parser.utils.segmentation import TextSegmenter


class TestTextSegmenter(unittest.TestCase):
    def test_segment_with_language(self):
        text_segmenter = TextSegmenter(
            "This is a sentence. This is another one.", language="en"
        )
        sentences = text_segmenter.segment()
        assert len(sentences) == 2
        assert sentences[0] == "This is a sentence."
        assert sentences[1] == "This is another one."

    def test_segment_without_language(self):
        text_segmenter = TextSegmenter("This is a sentence. This is another one.")
        sentences = text_segmenter.segment()
        assert len(sentences) == 2
        assert sentences[0] == "This is a sentence."
        assert sentences[1] == "This is another one."

    def test_segment_unsupported_language(self):
        text_segmenter = TextSegmenter(
            "This is a sentence. This is another one.", language="xyz"
        )
        with self.assertWarns(Warning) as cm:
            sentences = text_segmenter.segment()

        with self.subTest("Still works"):
            assert len(sentences) == 2
            assert sentences[0] == "This is a sentence."
            assert sentences[1] == "This is another one."

        with self.subTest("Warning message"):
            self.assertEqual(
                cm.warning.args[0],
                "Language 'xyz' not supported by sentence splitter, falling back to en for sentence splitting.",
            )

    def test_segment_empty_text(self):
        text_segmenter = TextSegmenter("")
        sentences = text_segmenter.segment()
        assert sentences == []
