import os.path
import tempfile

import iso639
from nltk.tokenize import word_tokenize
from symspellpy import SymSpell, Verbosity

from .model_utils import nltk_cache_download, SymspellSource
from .llm_correction.main import parse_output, generate_output, get_language_name
from .symspell_flair.text_correction import CorrectableText, FreqDict

DIR_MODELS = "/MODELS"
DIRNAME_SYMSPELL = os.path.join(DIR_MODELS, "symspell")

nltk_cache_download("punkt")


def correct_text_dummy(text: str) -> str:
    """
    This method is a dummy method that returns the input text as is.
    :param text:
    :return:
    """
    return text


def correct_text_symspell(text: str, language: str = None) -> str:
    """
    Based on similar spelling - SymSpell
    :param text:
    :param language: Language code, if None, defaults to "en" (English)
    :return:
    """

    if language is None:
        language = "en"

    l_source = SymspellSource().get_sources(language, fallback="en")

    try:
        language_name = get_language_name(language)
    except iso639.NonExistentLanguageError:
        print(f"Language code {language} not found, defaulting to English")
        # Default to English
        language_name = "english"

    try:
        words = word_tokenize(text, language_name.lower())
    except LookupError:
        print(f"Language {language_name} not found, defaulting to English")
        # Default to English
        words = word_tokenize(text, "english")

    # Initialize symspellpy instance
    sym_spell = SymSpell(count_threshold=2)
    for source in l_source:
        sym_spell.load_dictionary(source, 0, 1)

    corrected_text = []
    for word in words:
        if word.isalpha():
            suggestions = sym_spell.lookup(
                word,
                Verbosity.CLOSEST,
                max_edit_distance=2,
                transfer_casing=True,
                include_unknown=True,
            )
            if suggestions:
                if len(suggestions) > 1:
                    print(f"Multiple suggestions found: {len(suggestions)}")
                corrected_text.append(suggestions[0].term)
            else:
                corrected_text.append(word)
        else:
            corrected_text.append(word)
    corrected_text = (
        " ".join(corrected_text)
        .replace(" ,", ",")
        .replace(" .", ".")
        .replace(" ' ", "'")
    )
    return corrected_text


def prep_freq_dict(
    language: str,
    count_threshold,
    max_dictionary_edit_distance,
    log,
) -> FreqDict:
    freq_dict = FreqDict(
        count_threshold=count_threshold,
        max_dictionary_edit_distance=max_dictionary_edit_distance,
        log=log,
    )

    sources_filtered = SymspellSource().get_sources(language, fallback="en")

    for source in sources_filtered:
        freq_dict.update(source)

    return freq_dict


def correct_text_symspell_flair_cli(
    text: str,
    language: str,
    count_threshold=None,
    max_dictionary_edit_distance=None,
    log=None,
    fast=True,
    *args,
    **kwargs,
) -> str:
    """
    Based on Tom's CLI code
    :param text:
    :return:
    """

    freq_dict = prep_freq_dict(
        language, count_threshold, max_dictionary_edit_distance, log
    )

    with tempfile.TemporaryDirectory() as tmp_dirname:
        tmp_file = os.path.join(tmp_dirname, "tmp.txt")
        with open(tmp_file, "w") as f:
            f.write(text)

        tmp_out = os.path.join(tmp_dirname, "corrected.txt")

        correctable_text = CorrectableText(
            tmp_file,
            tmp_out,
            freq_dict,
            *args,
            modelcacheroot=os.path.join(DIR_MODELS, "flair"),
            log=log,
            **kwargs,
        )
        correctable_text.correct(fast=fast)

        with open(tmp_out, "r") as f:
            return f.read()


def correct_llm(text: str, language: str = None, prompt: str = None) -> str:
    """
    Correct text using a Large Language Model
    :param text:
    :return:
    """

    output = generate_output(text, lang_code=language, prompt=prompt)

    correction = parse_output(output)

    return correction
