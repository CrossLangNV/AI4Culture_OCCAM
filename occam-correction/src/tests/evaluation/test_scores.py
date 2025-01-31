import unittest

from evaluation.scores import (
    BLEU_corpus,
    CER_corpus,
    ChrF_corpus,
    TER_corpus,
    edit_distance_corpus,
)


class TestCorpusMetricShared(unittest.TestCase):
    """
    Superclass for corpus metrics
    """

    def setUp(self) -> None:
        self.l_ref = ["A B C", "B", "C", "I am a sentence"]
        self.l_hypo = ["C B A", "bb", "C", "I might be a sentence"]


class TestCorpusBLEU(TestCorpusMetricShared):
    def setUp(self) -> None:
        super().setUp()
        self.metric = BLEU_corpus

    def test_metric(self):
        score = self.metric(self.l_ref, self.l_hypo)

        self.assertAlmostEqual(score, 0.2066, delta=0.0001)

    def test_perfect(self):
        score = self.metric(self.l_ref, self.l_ref)

        self.assertAlmostEqual(score, 1.0, delta=0.0001)


class TestCorpusCER(TestCorpusMetricShared):
    def setUp(self) -> None:
        super().setUp()
        self.metric = CER_corpus

    def test_metric(self):
        score = self.metric(self.l_ref, self.l_hypo)

        self.assertAlmostEqual(score, 0.5455, delta=0.0001)

    def test_perfect(self):
        score = self.metric(self.l_ref, self.l_ref)

        self.assertAlmostEqual(score, 0.0, delta=0.0001)

    def test_worst(self):
        score = self.metric(self.l_ref, [""] * len(self.l_ref))

        self.assertAlmostEqual(score, 1.0, delta=0.0001)


class TestCorpusCHRF(TestCorpusMetricShared):
    def setUp(self) -> None:
        super().setUp()
        self.metric = ChrF_corpus

    def test_metric(self):
        score = self.metric(self.l_ref, self.l_hypo)

        self.assertAlmostEqual(score, 0.6066, delta=0.0001)

    def test_perfect(self):
        score = self.metric(self.l_ref, self.l_ref)

        self.assertAlmostEqual(score, 1.0, delta=0.0001)


class TestCorpusED(TestCorpusMetricShared):
    def setUp(self) -> None:
        super().setUp()
        self.metric = edit_distance_corpus

    def test_metric(self):
        score = self.metric(self.l_ref, self.l_hypo)

        self.assertAlmostEqual(score, 0.4138, delta=0.0001)

    def test_perfect(self):
        score = self.metric(self.l_ref, self.l_ref)

        self.assertAlmostEqual(score, 0.0, delta=0.0001)


class TestCorpusTER(TestCorpusMetricShared):
    def setUp(self) -> None:
        super().setUp()
        self.metric = TER_corpus

    def test_metric(self):
        score = self.metric(self.l_ref, self.l_hypo)

        self.assertAlmostEqual(score, 0.5556, delta=0.0001)

    def test_perfect(self):
        score = self.metric(self.l_ref, self.l_ref)

        self.assertAlmostEqual(score, 0.0, delta=0.0001)
