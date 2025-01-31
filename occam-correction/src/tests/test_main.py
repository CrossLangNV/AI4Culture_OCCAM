import os.path
import time
import unittest

from sacrebleu import TER

from post_ocr_correction.main import (
    correct_text_symspell,
    correct_text_symspell_flair_cli,
    correct_llm,
)


def error_test(ref: str, hyp: str) -> float:
    """
    This method returns an error rate of two strings
    "Lower is better"
    :param ref: Reference (GT)
    :param hyp: Hypothesis (OCR)
    :return:
    """

    # Translation edit rate
    ter = TER()
    corpus_ter = ter.corpus_score(hyp, [ref])
    corpus_ter = corpus_ter.score / 100

    return corpus_ter


class TestScore(unittest.TestCase):
    def test_perfect(self):
        text = "misdlen Self Indulgence, scrivent ahrègé M57 est un groupe d'étutropunt américain, onigiraire de New Yek. leur musique est formée d'un nélange de hipobop, puk rock, rock alternatif, electronia, sechno et musique isdurtrielle. le nom du greupe provient d'un alham du chonteur Sinmy Arire et de sen père enregistré en 1995."

        error = error_test(text, text)
        self.assertEqual(error, 0.0, "The error score should be 0.0")

    def test_perfect2(self):
        text_correct = "Mindless Self Indulgence, souvent abrégé MSI est un groupe d'electropunk américain, originaire de New York. Leur musique est formée d'un mélange de hip-hop, punk rock, rock alternatif, electronica, techno et musique industrielle. Le nom du groupe provient d'un album du chanteur Jimmy Urine et de son père enregistré en 1995."

        error = error_test(text_correct, text_correct)
        self.assertEqual(error, 0.0, "The error score should be 0.0")


class TestCorrectTextSymspell(unittest.TestCase):
    def setUp(self) -> None:
        self.method = correct_text_symspell

        filename = os.path.join(os.path.dirname(__file__), "data", "textfile.nl")
        with open(filename, "r") as f:
            self.text_nl = f.read()

        filename = os.path.join(os.path.dirname(__file__), "data", "textfile.en")
        with open(filename, "r") as f:
            self.text_en = f.read()

    def test_correct_text_symspell_en_simple(self):
        text = "Id ish wiht gret plasure"
        text_correct = "It is with great pleasure"
        text_expected = "Id is with great pleasure"  # Might ignore capitalization

        language = "en"

        text_corrected = self.method(text, language=language)

        score_before = error_test(text, text_correct)
        score_corrected = error_test(text_corrected, text_correct)

        print(f"Error went from {score_before} to {score_corrected}")

        with self.subTest("Error"):
            self.assertLess(
                score_corrected,
                score_before,
                "The error score after correction should be reduced",
            )

        with self.subTest("Text"):
            self.assertEqual(text_expected, text_corrected)

    def test_correct_text_symspell_en(self):
        text_correct = "It is with great pleasure, that I introduce to you a new member of our team. John Doe will be joining us starting next week as a Jr. Developer. John has a B.S. in Computer Science from the University of Maryland and has worked for the past 2 years at a Fortune 500 company. John will be a great addition to our company and we are excited to have him."
        text = "It sis with great pleasure,m taht I introduce to you a new memger of tour teanm. John doe will bejoijngin us ttarting nest t week as jr. dEvloper. John s has A b,s , I n computer Science forom the dUniveristy of Maryland and has wordkeyd for the wpaste 2 years at thea Fortune 500 companyh. JOhn will be a great additon to aour company and we are excited to havi im."

        text_corrected = self.method(text)

        score_before = error_test(text, text_correct)
        score_corrected = error_test(text_corrected, text_correct)

        print(f"Error went from {score_before} to {score_corrected}")

        print(f"Original: {text}")
        print(f"Corrected: {text_corrected}")

        self.assertLess(
            score_corrected,
            score_before,
            "The error score after correction should be reduced",
        )

    # @unittest.skip("Does not support other languages than English")
    def test_correct_text_symspell_fr(self):
        text = "misdlen Self Indulgence, scrivent ahrègé M57 est un groupe d'étutropunt américain, onigiraire de New Yek. leur musique est formée d'un nélange de hipobop, puk rock, rock alternatif, electronia, sechno et musique isdurtrielle. le nom du greupe provient d'un alham du chonteur Sinmy Arire et de sen père enregistré en 1995."

        text_correct = "Mindless Self Indulgence, souvent abrégé MSI est un groupe d'electropunk américain, originaire de New York. Leur musique est formée d'un mélange de hip-hop, punk rock, rock alternatif, electronica, techno et musique industrielle. Le nom du groupe provient d'un album du chanteur Jimmy Urine et de son père enregistré en 1995."

        text_corrected = self.method(text, language="fr")

        score_before = error_test(text, text_correct)
        score_corrected = error_test(text_corrected, text_correct)

        print(f"Error went from {score_before} to {score_corrected}")

        self.assertNotEquals(
            score_corrected,
            score_before,
            "The error score after correction should be reduced",
        )

        # Did not improve
        if 0:
            self.assertLess(
                score_corrected,
                score_before,
                "The error score after correction should be reduced",
            )

    def test_unknown_language_1(self):
        """
        Should fall back to English
        :return:
        """
        lang = "yy"
        text_corrected = self.method(self.text_nl, lang)

        with self.subTest("Non-empty"):
            self.assertTrue(text_corrected.strip(), "The text should not be empty")

        with self.subTest("Change"):
            error = error_test(self.text_nl, text_corrected)
            print(f"Error: {error}")
            self.assertGreater(error, 0.0, "The error score should be greater than 0.0")

    def test_unknown_language_2(self):
        """
        Should fall back to English
        :return:
        """
        lang = "yy"
        text_corrected = self.method(self.text_en, lang)

        with self.subTest("Non-empty"):
            self.assertTrue(text_corrected.strip(), "The text should not be empty")

        with self.subTest("Change"):
            error = error_test(self.text_en, text_corrected)
            print(f"Error: {error}")
            self.assertGreater(error, 0.0, "The error score should be greater than 0.0")

        with self.subTest("Original output"):
            text_original = "this is a spelling mistake\nhe ran to the enormous house in the nighebouring street\nthey were spelling at the window\n"
            self.assertEqual(
                text_corrected, " ".join(text_original.split()), "Original code output"
            )

    def test_it(self):
        """
        Bug reported on 21/05/2024: Italian lexicon not loaded
        :return:
        """

        text = """
            come quando si mette, il pepse sulla minerzza
            alle q. si aveva il pans non più di mezza
            pagnotta, ct Testa che era ni nera che noi
            si sapera neppste noci chi nome daigli
            e più scarsa che allondante.
            A mezzogiorno si avevo il rancio al solito acqua
            ò Rroso di patate cos sappena mungiato
            questo si aveva il rago non più di tre
            patate a Testa, poci Sopo averi sbaffato tutti
            guesto la pempa cominciava andare in
            Opera
            Alla tera alle 8. Salvo Sun sbalio sempre il
            medesimo rancio, gave col brodo purò inten
            bianocci più acqua che fave, e quando si
            Trovava il capo baracca ulziaco senza vini
            si aveva la polenta, che ferta
            Dopo Dutti questi rancii chi sarà prero con
            qualche pricciola di pano per le daree sarà
            punido con un Ora di fucilazione alla
            seiena
            Oia chiungue manca a questi regolamennd
            sevenamente punito a termini di
            legge
            Il comitato e monto chi
             
            Gaone
        """

        language = "it"

        text_corrected = self.method(text, language=language)

        term_correct = "pepe"

        with self.subTest("Correct correction"):
            self.assertIn(
                term_correct, text_corrected, "The term should be in the corrected text"
            )

    def test_bug_2024_05_21(self):
        """
        Following text raised an error
        :return:
        """

        text = """
            Avviso
            Avendo nicevuto ordine del comando dupiumo
            dei inTervenire a pranzo di guerrà la
            Classe del 1886 al 1841 Sei riformaza
            s quelle delle casse del 1826 1783-94-94
            prossimamenta
            Zistino Viverii.
            di mongia se si può ma senzo reclumare
            Obiei Sa 309 con contorno di 200 prolunzat
            Bombe a mano in gran quantita con contorni
            dii gelatina exposiva. Carta al rugo col
            contorno du schegge di gradate, Ordinarie.
            tuttto misto manzia de necella di gereopsami
            Solei rarpine con confettri dhi piompo¬
            Pinfreseo di acqua piovuna delli altur di
            cortalta in quan quanteta, finito il pranzi
            Sanza Sinfonia alleggzia con Otieri da 290
            210 - piccola mistragliatieri raggi, lumpri
            lumienanti coscì la vesta avrò mola
            Turata Su Sala Bara illuminata
            progumata, con gas Offisiante, 3 rprego
            ci compagni dai intervenire mumita
            di mascesa per i ga0 isfessianta
            29 1 1916
        """

        language = "it"

        text_corrected = self.method(text, language=language)

        with self.subTest("correct term"):
            self.assertIn("ricevuto", text_corrected)

        text_flat = " ".join(map(str.strip, text.split()))

        text_corrected_flat = self.method(text_flat, language=language)

        with self.subTest("correct term - flat"):
            self.assertIn("ricevuto", text_corrected_flat)

    def test_bug_2024_06_05(self):
        """
        Short text raised an error
        :return:
        """
        text = "S"

        text_corrected = self.method(text)

        with self.subTest("correct"):
            self.assertEqual(text, text_corrected)


class TestCorrectTextSymspellFlair(unittest.TestCase):
    """
    FLAIR + SymSpell
    """

    def setUp(self):
        self.text = "Abc."
        self.text_correct = "Abc."
        self.freq_file = "Abc.freq"
        self.corpus_file = "Abc.corp"

        filename = os.path.join(os.path.dirname(__file__), "data", "textfile.nl")
        with open(filename, "r") as f:
            self.text_nl = f.read()

        filename = os.path.join(os.path.dirname(__file__), "data", "textfile.en")
        with open(filename, "r") as f:
            self.text_en = f.read()

            self.method = correct_text_symspell_flair_cli

    def test_main(self):
        """
        Based on Tom's CLI
        :return:
        """

        text_corrected = correct_text_symspell_flair_cli(self.text, "en")

        self.assertTrue(text_corrected.strip(), "The text should not be empty")

        with self.subTest("Original output"):
            text_original = "Abc.\n"
            self.assertEqual(text_corrected, text_original, "Original code output")

    def test_nl(self):
        text_corrected = correct_text_symspell_flair_cli(self.text_nl, "nl")

        error = error_test(self.text_nl, text_corrected)
        print(f"Error: {error}")

        self.assertGreater(error, 0.0, "The error score should be greater than 0.0")

        with self.subTest("Original output"):
            text_original = "Gister ontving ik pakje "
            self.assertEqual(
                text_corrected[: len(text_original)],
                text_original,
                "Original code output",
            )

    def test_en(self):
        text_corrected = correct_text_symspell_flair_cli(self.text_en, "en")

        error = error_test(self.text_en, text_corrected)
        print(f"Error: {error}")

        self.assertGreater(error, 0.0, "The error score should be greater than 0.0")

        with self.subTest("Original output"):
            text_original = "this is a spelling mistake\nhe ran to the enormous house in the nighebouring street\nthey were spelling at the window\n"
            self.assertEqual(text_corrected, text_original, "Original code output")

    def test_unknown_language_1(self):
        """
        Should fall back to English
        :return:
        """
        lang = "yy"
        text_corrected = correct_text_symspell_flair_cli(self.text_nl, lang)

        with self.subTest("Non-empty"):
            self.assertTrue(text_corrected.strip(), "The text should not be empty")

        with self.subTest("Change"):
            error = error_test(self.text_nl, text_corrected)
            print(f"Error: {error}")
            self.assertGreater(error, 0.0, "The error score should be greater than 0.0")

    def test_unknown_language_2(self):
        """
        Should fall back to English
        :return:
        """
        lang = "yy"
        text_corrected = correct_text_symspell_flair_cli(self.text_en, lang)

        with self.subTest("Non-empty"):
            self.assertTrue(text_corrected.strip(), "The text should not be empty")

        with self.subTest("Change"):
            error = error_test(self.text_en, text_corrected)
            print(f"Error: {error}")
            self.assertGreater(error, 0.0, "The error score should be greater than 0.0")

        with self.subTest("Original output"):
            text_original = "this is a spelling mistake\nhe ran to the enormous house in the nighebouring street\nthey were spelling at the window\n"
            self.assertEqual(text_corrected, text_original, "Original code output")

    def test_bug_1(self):
        """
        Reported on 13/05/2024

        |   File "/tmp/src/post_ocr_correction/symspell_flair/text_correction.py", line 301, in __correct_line
        |     corrected_line = self.__detokenize(line, words, corrected_words)
        |   File "/tmp/src/post_ocr_correction/symspell_flair/text_correction.py", line 437, in __detokenize
        |     i += len(words[wordid])
        | IndexError: list index out of range

        :return:
        """

        b_newlines = 1
        if b_newlines:
            text = """come quando si mette, il pepse sulla minerzza
                alle q. si aveva il pans non più di mezza
                pagnotta, ct Testa che era ni nera che noi
                si sapera neppste noci chi nome daigli
                e più scarsa che allondante.
                A mezzogiorno si avevo il rancio al solito acqua
                ò Rroso di patate cos sappena mungiato
                questo si aveva il rago non più di tre
                patate a Testa, poci Sopo averi sbaffato tutti
                guesto la pempa cominciava andare in
                Opera
                Alla tera alle 8. Salvo Sun sbalio sempre il
                medesimo rancio, gave col brodo purò inten
                bianocci più acqua che fave, e quando si
                Trovava il capo baracca ulziaco senza vini
                si aveva la polenta, che ferta
                Dopo Dutti questi rancii chi sarà prero con
                qualche pricciola di pano per le daree sarà
                punido con un Ora di fucilazione alla
                seiena
                Oia chiungue manca a questi regolamennd
                sevenamente punito a termini di
                legge
                Il comitato e monto chi
                 
                Gaone
            """

            text = "\n".join(map(str.strip, text.split("\n"))) + "\n"

            text_corrected = correct_text_symspell_flair_cli(text, "it")

            with self.subTest("Change"):
                error = error_test(text, text_corrected)
                print(f"Error: {error}")
                self.assertGreater(
                    error, 0.0, "The error score should be greater than 0.0"
                )

            with self.subTest("Same length"):
                self.assertEqual(
                    len(text.splitlines()),
                    len(text_corrected.splitlines()),
                    "The number of lines should be the same",
                )

        text_gateway = "come quando si mette, il pepse sulla minerzza alle q. si aveva il pans non più di mezza pagnotta, ct Testa che era ni nera che noi si sapera neppste noci chi nome daigli e più scarsa che allondante. A mezzogiorno si avevo il rancio al solito acqua ò Rroso di patate cos sappena mungiato questo si aveva il rago non più di tre patate a Testa, poci Sopo averi sbaffato tutti guesto la pempa cominciava andare in Opera Alla tera alle 8. Salvo Sun sbalio sempre il medesimo rancio, gave col brodo purò inten bianocci più acqua che fave, e quando si Trovava il capo baracca ulziaco senza vini si aveva la polenta, che ferta Dopo Dutti questi rancii chi sarà prero con qualche pricciola di pano per le daree sarà punido con un Ora di fucilazione alla seiena Oia chiungue manca a questi regolamennd sevenamente punito a termini di legge Il comitato e monto chi   Gaone"
        text_corrected = correct_text_symspell_flair_cli(text_gateway, "it")

    def test_bug_2(self):
        """
        Reported on 14/05/2024
        """

        b_newlines = 1
        if b_newlines:
            text = """
                Mavlava Concentramento della Prigionia del lunvo
                2l Maggir 1910
                Compagnia dal Cipluc
                E severamende proilito a bever vino chi
                sarà preso a fare questo atto sarà punito
                con 10 anni di carcere duro, e 9 Ori
                Si palo al giorno.
                Vitto si prego al Signori di Nui
                ai seguenti regolament
                Inquanto al mangiare si prega di noni
                mangiari più di 3 VV le al giorno, cioè
                al mattino acqua calda con ci p0 di farina
                si castagni vindhe o pure farina di favi
            """

            text = "\n".join(map(str.strip, text.split("\n"))) + "\n"

            text_corrected = correct_text_symspell_flair_cli(text, "it")

            with self.subTest("Change"):
                error = error_test(text, text_corrected)
                print(f"Error: {error}")
                self.assertGreater(
                    error, 0.0, "The error score should be greater than 0.0"
                )

            with self.subTest("Same length"):
                self.assertEqual(
                    len(text.splitlines()),
                    len(text_corrected.splitlines()),
                    "The number of lines should be the same",
                )

        text_gateway = "Mavlava Concentramento della Prigionia del lunvo 2l Maggir 1910 Compagnia dal Cipluc E severamende proilito a bever vino chi sarà preso a fare questo atto sarà punito con 10 anni di carcere duro, e 9 Ori Si palo al giorno. Vitto si prego al Signori di Nui ai seguenti regolament Inquanto al mangiare si prega di noni mangiari più di 3 VV le al giorno, cioè al mattino acqua calda con ci p0 di farina si castagni vindhe o pure farina di favi"
        text_corrected = correct_text_symspell_flair_cli(text_gateway, "it")

    def test_bug_3(self):
        """
        Reported on 14/05/2024
        """

        text = """
           per Fra giorni ci sarte un sol pans con u¬
            rancio che rifiutano ci cani scefa sati con
            non ditumanci e con voii lodio per tempr
            Sazi
            Al lavoro mavete pontato peggio anco
            Sei sciavi venduti a piedi scalgi affar
            battuti senza aver compazione pietà.
            Innocinticiavete puiti con ferri con pal
            si prigione e deci viliacchi non ve patragore
            che far soffrire coss un prigiorve
            Cd il palo Nrumento crutete colle mani didietro
            legate sulla funda Sui piedi soltevate per sue
            Abbiuni risto in uno sol vola Precento
            rumi al pal malesetto la baionetta puntati
            nel petto e chi si muove neciso sarà
            Agugzimi di Cassa galera anstniaci
            geroni è beciale cn maltrattasti al par¬
            Sanimali maledetta sla pazzo utali
            Ol cara patria abbian fatto ntorni
            nella dell’italia civile nazione e
            Sall’aurtria la fams è il bastoris
            li tuoci fighi non sofroni
            11101
        """

        text = "\n".join(map(str.strip, text.split("\n"))) + "\n"

        text_corrected = correct_text_symspell_flair_cli(text, "it")

        with self.subTest("Change"):
            error = error_test(text, text_corrected)
            print(f"Error: {error}")
            self.assertGreater(error, 0.0, "The error score should be greater than 0.0")

        with self.subTest("Same length"):
            self.assertEqual(
                len(text.splitlines()),
                len(text_corrected.splitlines()),
                "The number of lines should be the same",
            )

    def test_bug_4(self):
        """
        Reported on 31/05/2024
        After a double space, words are suddenly concatenated
        """

        text = """
            par les bauchers du batail. lon.  Elle était encore bien dure. Touche 6 f. solde. A 4 heures rassemblement, départ à 5 heures pour St Nicolas. où nous arrivons vers 6h. Le billet de logement que je recois me conduit à 1 heure de la place, dans une ferme de la chaussée d'An¬ -vers. Souper avec du pain sec et, heureusement, de l'excellent jambon. Les habitants de la ferme sont tous flamands et c'est non sans peine que nous arrivons à nous faire comprendre. 24 août - Limidi - Réunion à la grand Place à 9 heures pour être passés en rexue à 10 heures par le général clooten. Nous sommes mis maintenant. tous les ordres d'un gêne ral militaire et verses dans la 5e division d'armée. Notre major nous dit que nous ne devons pas compter être rentres à Bruxelles d'ici deux mois. C'est encore rageant. Je m'achete un bonnet de police (1,75) un couteau et un mouchen.
              """
        text = "\n".join(map(str.strip, text.split("\n"))) + "\n"

        text_corrected = correct_text_symspell_flair_cli(text, "fr")

        with self.subTest("Change"):
            error = error_test(text, text_corrected)
            print(f"Error: {error}")
            self.assertGreater(error, 0.0, "The error score should be greater than 0.0")

        with self.subTest("Maintain spacing"):
            self.assertIn("  ", text_corrected, "There should be double spaces")

            self.assertNotIn("4heuresrassemblement", text_corrected)
            self.assertIn("4 heures rassemblement", text_corrected)

        with self.subTest("encoding"):
            self.assertIn("départ", text_corrected)

    def test_bug_2024_06_05(self):
        """
        Short text raised an error
        :return:
        """
        text = "S"

        text_corrected = self.method(text, "")

        with self.subTest("correct"):
            self.assertEqual(text, text_corrected.strip())

    @unittest.skip("This test takes too long")
    def test_language_parameter(self):
        text_corrected_nl = correct_text_symspell_flair_cli(self.text_nl, "nl")
        text_corrected_en = correct_text_symspell_flair_cli(self.text_nl, "en")

        error_nl = error_test(self.text_nl, text_corrected_nl)
        error_en = error_test(self.text_nl, text_corrected_en)

        print(f"Error NL: {error_nl}")
        print(f"Error EN: {error_en}")

        self.assertNotEquals(
            error_nl, error_en, "Dutch and English output should be different"
        )

    @unittest.skip("This test takes too long")
    def test_speed(self):
        t0 = time.time()
        text_corrected_fast = correct_text_symspell_flair_cli(
            self.text_nl, "nl", fast=True
        )
        t1 = time.time()
        t_fast = t1 - t0

        t0 = time.time()
        text_corrected_slow = correct_text_symspell_flair_cli(
            self.text_nl, "nl", fast=False
        )
        t1 = time.time()
        t_slow = t1 - t0

        print(f"Fast: {t_fast}")
        print(f"Slow: {t_slow}")

        self.assertLess(t_fast, t_slow, "Fast should be faster than slow")


class TestCorrectTextLLM(unittest.TestCase):
    """
    LLM
    """

    def setUp(self):
        self.method = correct_llm

        self.text = "Abc."
        self.text_correct = "Abc."
        self.freq_file = "Abc.freq"
        self.corpus_file = "Abc.corp"

        filename = os.path.join(os.path.dirname(__file__), "data", "textfile.nl")
        with open(filename, "r") as f:
            self.text_nl = f.read()

        filename = os.path.join(os.path.dirname(__file__), "data", "textfile.en")
        with open(filename, "r") as f:
            self.text_en = f.read()

    def test_main(self):
        text_corrected = self.method(self.text)

        self.assertTrue(text_corrected.strip(), "The text should not be empty")

        with self.subTest("Original output"):
            text_correct = "Abc."
            self.assertEqual(text_corrected, text_correct, "Original code output")

    def test_nl(self):
        text_corrected = self.method(self.text_nl, "nl")

        error = error_test(self.text_nl, text_corrected)
        print(f"Error: {error}")

        self.assertGreater(error, 0.0, "The error score should be greater than 0.0")

        with self.subTest("Original output"):
            text_correct = "Gister ontving ik pakje "
            self.assertEqual(
                text_corrected[: len(text_correct)],
                text_correct,
                "Original code output",
            )

    def test_en(self):
        text_corrected = self.method(self.text_en, "en")

        error = error_test(self.text_en, text_corrected)
        print(f"Error: {error}")

        self.assertGreater(error, 0.0, "The error score should be greater than 0.0")

        with self.subTest("Original output"):
            text_correct = "this is a spelling mistake   he ran to the enormous house in the neighboring street   they were spelling at the window"
            self.assertEqual(text_correct, text_corrected, "Original code output")

    def test_language_parameter(self):
        text_corrected_nl = self.method(self.text_nl, "nl")
        text_corrected_en = self.method(self.text_nl, "en")

        error_nl = error_test(self.text_nl, text_corrected_nl)
        error_en = error_test(self.text_nl, text_corrected_en)

        print(f"Error NL: {error_nl}")
        print(f"Error EN: {error_en}")

        self.assertNotEquals(
            error_nl, error_en, "Dutch and English output should be different"
        )
