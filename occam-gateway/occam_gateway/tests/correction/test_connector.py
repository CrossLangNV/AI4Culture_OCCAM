import unittest


from correction.connector import CorrectionConnector


class TestLocalOcrConnector(unittest.TestCase):
    def setUp(self) -> None:
        self.connector = CorrectionConnector()

    def test_sym_spell_response(self):
        language = "fr"
        text = "misdlen Self Indulgence, scrivent ahrègé M57 est un groupe d'étutropunt américain, onigiraire de New Yek. leur musique est formée d'un nélange de hipobop, puk rock, rock alternatif, electronia, sechno et musique isdurtrielle. le nom du greupe provient d'un alham du chonteur Sinmy Arire et de sen père enregistré en 1995."

        data = self.connector.correct_sym_spell(text, language)

        text_corrected = data.text

        with self.subTest("Non-empty response"):
            self.assertTrue(text_corrected)

        with self.subTest("Correct response"):
            self.assertNotEqual(text, text_corrected)

    def test_sym_spell_flair(self):
        language = "en"
        text = "Beneficiary may appoint in writing a subistition fr succesor trusste, succedeing to all rights."

        data = self.connector.correct_sym_spell_flair(text, language)

        text_corrected = data.text

        with self.subTest("Non-empty response"):
            self.assertTrue(text_corrected)

        with self.subTest("Correct response"):
            self.assertIn("successor", text_corrected)
