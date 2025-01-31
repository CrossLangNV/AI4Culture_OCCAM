import os.path
import unittest


from okapi_segmentation.main import main, okapi_segmentation


DIRNAME_FILES = os.path.join(os.path.dirname(__file__), "data")
FILENAME_IN = os.path.join(DIRNAME_FILES, "test_segmentation.txt")
FILENAME_OUT = os.path.join(DIRNAME_FILES, "test_segmentation_tmp.txt")
FILENAME_REF = os.path.join(DIRNAME_FILES, "test_segmentation_ref.txt")


class OkapiSegmentationTest(unittest.TestCase):
    def setUp(self):
        with self.subTest("Sanity check"):
            self.assertTrue(
                os.path.exists(FILENAME_IN), f"Input file {FILENAME_IN} does not exist"
            )
            self.assertTrue(
                os.path.exists(FILENAME_REF),
                f"Reference file {FILENAME_REF} does not exist",
            )

    def test_okapi_segmentation(self):
        main(FILENAME_IN, FILENAME_OUT, "en")

        with self.subTest("File exists"):
            self.assertTrue(os.path.exists(FILENAME_OUT))

        with self.subTest("Content"):
            with open(FILENAME_OUT) as f:
                text = f.read()

            with open(FILENAME_REF) as f:
                text_ref = f.read()

            self.assertEqual(text, text_ref)

    def test_files_not_exist(self):
        with self.assertRaises(Exception):
            main(filename_in="nonexistent.txt")

    def test_okapi_segmentation_text(self):
        with open(FILENAME_IN) as f:
            text = f.read()
            lines = list(map(str.strip, text.splitlines()))

        with self.subTest("Sanity check - lines"):
            self.assertEqual(len(lines), 3)
            self.assertEqual(lines[0], lines[0].strip())
            self.assertEqual(lines[1], lines[1].strip())
            self.assertEqual(lines[2], lines[2].strip())

        lines_segmented = okapi_segmentation(lines)

        with self.subTest("Split"):
            self.assertGreater(len(lines_segmented), len(lines))

        with self.subTest("No trailing and leading whitespace"):
            for line in lines_segmented:
                self.assertEqual(line, line.strip())

        with self.subTest("Last line not empty"):
            self.assertTrue(lines_segmented[-1])
