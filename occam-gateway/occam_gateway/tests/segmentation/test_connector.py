import unittest


from segmentation.connector import SegmentationConnector, SegmentationOption


class SegmentationConnectorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.connector = SegmentationConnector()

    def test_health(self):
        self.assertTrue(self.connector.health())

    def test_pipeline_options(self):
        self.connector.assert_options_up_to_date()

    def test_pipeline_options_raise(self):
        self.connector.OPTIONS = ["not an option"]
        with self.assertRaises(Exception):
            self.connector.assert_options_up_to_date()

    def test_pipeline(self):
        data = {
            "text_lines": [
                "This is a sent-",
                "ence. This is",
                "another sentence.",
                "As you can see, it",
                "is split over multi-",
                "ple lines.",
            ],
            "language": "en",
            "options": [
                SegmentationOption(name="dehyphenation"),
                SegmentationOption(name="join_lines"),
                SegmentationOption(name="sentence_segmentation/okapi"),
            ],
        }

        response = self.connector.pipeline(**data)

        text_segmented = response.lines

        self.assertListEqual(
            text_segmented,
            [
                "This is a sentence.",
                "This is another sentence.",
                "As you can see, it is split over multiple lines.",
            ],
        )
