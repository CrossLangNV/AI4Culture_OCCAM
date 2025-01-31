from unittest import TestCase

from post_ocr_correction.symspell_flair.embeddingsCL import FlairEmbeddingsCL


class TestLanguageModelCL(TestCase):
    def setUp(self, lang="multi", fast=True) -> None:
        fast_suffix = "-fast" if fast else ""

        model_name = f"{lang}-forward{fast_suffix}"
        self.lm_forward = FlairEmbeddingsCL(model_name, has_decoder=True).lm
        model_name = f"{lang}-backward{fast_suffix}"
        self.lm_backward = FlairEmbeddingsCL(model_name, has_decoder=True).lm

        self.text = "This is a test"

    def test_calculate_perplexity_forward_single(self):
        self._test_single(self.lm_forward)

    def test_calculate_perplexity_forward_multiple(self):
        self._test_multiple(self.lm_forward)

    def test_calculate_perplexity_backward_single(self):
        self._test_single(self.lm_backward)

    def test_calculate_perplexity_backward_multiple(self):
        self._test_multiple(self.lm_backward)

    def _test_single(self, lm):
        """
        Test the perplexity of a single text is calculated correctly
        :return:
        """
        perplexity = lm.calculate_perplexity(self.text)
        l_perplexity = lm.calculate_perplexity_multi([self.text])

        self.assertAlmostEqual(perplexity, l_perplexity[0], places=3)

    def _test_multiple(self, lm):
        """
        Output should be the same as the single perplexity even when multiple texts are given
        :return:
        """
        l_text = [self.text, self.text + " another one"]

        perplexity = lm.calculate_perplexity(self.text)
        perplexity_multi = lm.calculate_perplexity_multi(l_text)[0]
        perplexity_single = lm.calculate_perplexity_multi([self.text])[0]

        with self.subTest("Single vs Multiple at the same time"):
            self.assertAlmostEqual(perplexity_single, perplexity_multi, places=5)
        with self.subTest("Original perplexity"):
            self.assertAlmostEqual(perplexity, perplexity_multi, places=3)
