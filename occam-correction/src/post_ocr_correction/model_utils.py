import glob
import os

import nltk

DIR_MODELS = "/MODELS"
DIR_TOKENIZERS = os.path.join(DIR_MODELS, "tokenizers")
DIRNAME_SYMSPELL = os.path.join(DIR_MODELS, "symspell")
DIRNAME_FLAIR = os.path.join(DIR_MODELS, "flair")


def nltk_cache_download(name: str):
    """
    Check if tokenizer is already cached, else download
    :param name:
    :return:
    """

    try:
        nltk.data.find(os.path.join("tokenizers", name), paths=[DIR_MODELS])
    except LookupError:
        nltk.download("punkt", download_dir=DIR_MODELS)

    if DIR_MODELS not in nltk.data.path:
        nltk.data.path.append(DIR_MODELS)


class LanguageNotSupportedError(ValueError):
    pass


class SymspellSource:
    def get_sources(self, language: str, fallback: str = None) -> list[str]:
        """
        Get the freq file for the given language
        :param language: language code
        :param fallback: language code to fallback to if the given language is not supported
        :return:
        """

        language = language.lower()

        _source = f"{language}-*.freq"
        _source = os.path.join(DIRNAME_SYMSPELL, _source)

        if l_source := glob.glob(_source):
            print(f"Using frequency dictionary for language {language}")
            return l_source

        # Language not found

        if fallback is not None:
            print(
                f"No frequency dictionary found for language {language}, defaulting to English"
            )
            return self.get_sources(fallback, fallback=None)

        message = f"Language {language} not yet supported"
        print(message)
        raise LanguageNotSupportedError(message)
