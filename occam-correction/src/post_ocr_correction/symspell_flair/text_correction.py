import itertools
import logging
import os
import sys
from pathlib import Path

from nltk.tokenize import word_tokenize

# https://pypi.org/project/symspellpy/
# dictionary files reside in https://github.com/wolfgarbe/SymSpell/tree/master/SymSpell.FrequencyDictionary
from symspellpy import SymSpell, Verbosity
from symspellpy.suggest_item import SuggestItem

from .embeddingsCL import FlairEmbeddingsCL
from ..model_utils import nltk_cache_download, DIRNAME_SYMSPELL

logger = logging.getLogger(__name__)


class FreqDict:
    """
    a dictionary with frequencies
    if various sources are used, their frequencies are summed
    """

    def __init__(
        self, count_threshold=None, max_dictionary_edit_distance=None, log=False
    ):
        if count_threshold is None:
            count_threshold = 2
        if max_dictionary_edit_distance is None:
            max_dictionary_edit_distance = 2
        self.__count_threshold = count_threshold
        self.__max_dictionary_edit_distance = max_dictionary_edit_distance
        self.__log = log
        self.__sym_spell = SymSpell(
            max_dictionary_edit_distance=max_dictionary_edit_distance,
            count_threshold=count_threshold,
        )
        self.__sources: list[str] = []

    def update(self, source: str):
        # If source file has no folder information, the default folder is used
        if not os.path.dirname(source):
            source = os.path.join(DIRNAME_SYMSPELL, source)

        try:
            parts = os.path.splitext(source)
            if parts[1] == ".freq":
                if self.__log:
                    print(f"{source}: updating dictionary with frequency list")
                self.__sym_spell.load_dictionary(source, 0, 1)
            else:
                if self.__log:
                    print(
                        f"{source} is a file containing corpus: creating frequency list from file, updating dictionary, writing resulting entries to {source}.freq"
                    )
                self.__sym_spell.create_dictionary(source)
                with open(source + ".freq", "w") as f:
                    for word in sorted(
                        self.__sym_spell.words,
                        key=lambda x: self.__sym_spell.words[x],
                        reverse=True,
                    ):
                        f.write(word + " " + str(self.__sym_spell.words[word]) + "\n")
            self.__sources.append(source)
        except Exception as e:
            print(e)
            print("exiting")
            sys.exit()

    def get(self, word: str) -> int:
        return self.__sym_spell.words.get(word, 0)

    def get_closest_words(self, word: str) -> list[SuggestItem]:
        return self.__sym_spell.lookup(
            word, Verbosity.CLOSEST, transfer_casing=True, include_unknown=True
        )

    def __repr__(self):
        return (
            "FreqDict(max_dictionary_edit_distance=%r, count_threshold=%r, log=%r)"
            % (self.__max_dictionary_edit_distance, self.__count_threshold, self.__log)
        )

    def __str__(self):
        result = (
            f"frequency dictionary: max_dictionary_edit_distance {self.__max_dictionary_edit_distance}, count_threshold {self.__count_threshold}, logging {self.__log}\n"
            + f"sources used for building dictionary: {self.__sources}"
        )
        if len(self.__sources) > 0:
            result += "\nexample entries:"
            maxcount = 5
            for count, word in zip(range(maxcount), self.__sym_spell.words):
                if count == maxcount:
                    break
                result += f"\nword {word}, frequency {self.__sym_spell.words[word]}"
        return result


class WordSuggestions:
    """
    a list of SuggestItems sorted descendingly according to score
    """

    def __init__(
        self, word: str, freqdict: FreqDict, min_length_for_change=3, log=False
    ):
        self.__word = word
        self.__freqdict = freqdict
        self.__min_length_for_change = min_length_for_change
        self.__log = log
        self.__suggestions = None
        self.__establish()

    def __establish(self):
        try:
            if (
                self.__word.isalpha()
                and len(self.__word) >= self.__min_length_for_change
            ):
                self.__suggestions = self.__freqdict.get_closest_words(self.__word)
                # Add original word to suggestions if it is not in the dictionary
                if self.__freqdict.get(self.__word) == 0:
                    words = list(map(lambda x: x.term, self.__suggestions))
                    if self.__word not in words:
                        self.__suggestions.append(SuggestItem(self.__word, 0, 0))
            else:
                self.__suggestions = [
                    SuggestItem(self.__word, 0, self.__freqdict.get(self.__word))
                ]
        except Exception as e:
            print(e)
            print("exiting")
            sys.exit()

    def getSuggestItems(self) -> list[SuggestItem]:
        try:
            if self.__suggestions == None:
                raise ValueError("suggestions is not defined yet")
            else:
                return self.__suggestions
        except ValueError as e:
            print(e)
            print("exiting")
            sys.exit()

    def __repr__(self):
        return (
            "WordSuggestions(word=%r,freqdict=%r,min_length_for_change=%r,log=%r)"
            % (self.__word, self.__freqdict, self.__min_length_for_change, self.__log)
        )

    def __str__(self):
        result = (
            f"suggestions for word {self.__word} based on freqdict {self.__freqdict}\n"
            + f"with min_length_for_change {self.__min_length_for_change} and logging set to {self.__log}"
        )
        if self.__suggestions != None:
            result += ":"
            for item in self.__suggestions:
                result += (
                    f"\nword {item.term}, distance {item.distance}, count {item.count}"
                )
        return result


class Window:
    """
    a token window with a score
    """

    def __init__(self, startpos: int, tokens: list[str], score: float):
        self.__startpos = startpos
        self.__tokens = tokens
        self.__score = score

    @property
    def startpos(self) -> int:
        return self.__startpos

    @property
    def tokens(self) -> list[str]:
        return self.__tokens

    @property
    def score(self) -> float:
        return self.__score

    def get_size(self) -> int:
        return len(self.__tokens)

    def __repr__(self):
        return "Window(startpos=%r, tokens=%r, score=%r)" % (
            self.__startpos,
            self.__tokens,
            self.__score,
        )

    def __str__(self):
        return f"window {self.__tokens} starting at position {self.__startpos} with score {self.__score}, logging set to {self.__log}"


class CorrectableText:
    """
    text that may have to be corrected and that is stored in a file (one line per sentence)
    """

    def __init__(
        self,
        infilename: str,
        outfilename: str,
        freqdict: FreqDict,
        modelcacheroot=None,
        max_window_size=3,
        min_length_for_change=4,
        log=None,  # False by default
    ):
        if log is None:
            log = False

        self.__infilename = infilename
        self.__outfilename = outfilename
        self.__freqdict = freqdict
        self.__modelcacheroot = modelcacheroot
        self.__max_window_size = max_window_size
        self.__min_length_for_change = min_length_for_change
        self.__log = log
        self.__read_file()

    def __read_file(self):
        self.__lines: list[str] = []
        try:
            with open(Path(self.__infilename), "r") as f:
                for line in f:
                    line = line.rstrip()
                    self.__lines.append(line)
        except FileNotFoundError as e:
            print(e)
            print("exiting")
            sys.exit()

    def correct(self, fast=True):
        nltk_cache_download("punkt")
        self.__load_flair_models(fast=fast)

        self.__corrected_lines: list[str] = []
        for line in self.__lines:
            if not line.strip():
                self.__corrected_lines.append(line)
                continue

            self.__corrected_lines.append(self.__correct_line(line))

        self.__write_file()

    def __write_file(self):
        try:
            f = open(Path(self.__outfilename), "w")
        except Exception as e:
            print(e)
            print("exiting")
            sys.exit()
        else:
            for line in self.__corrected_lines:
                f.write(line + "\n")
        finally:
            f.close()

    def __load_flair_models(
        self, lang="multi", forward=True, backward=True, fast=False
    ):
        fast_suffix = "-fast" if fast else ""

        model_names: list[str] = []
        if forward:
            model_names.append(f"{lang}-forward{fast_suffix}")
        if backward:
            model_names.append(f"{lang}-backward{fast_suffix}")

        try:
            self.__lms = [
                FlairEmbeddingsCL(x, has_decoder=True).lm for x in model_names
            ]
        except Exception as e:
            print(e)
            print("exiting")
            sys.exit()

        if self.__log:
            print(self.__lms)
            print(self.__lms[0].calculate_perplexity("this is a"))

    def __correct_line(self, line: str) -> str:
        if self.__log:
            print("\n********** START correction of line:", line, "\n")

        words = word_tokenize(line)  # NLTK
        corrected_words = self.__correct_windows(words)
        corrected_line = self.__detokenize(line, words, corrected_words)

        if self.__log:
            print("\n********** END corrected line:", corrected_line, "\n")

        return corrected_line

    def __correct_windows(self, words: list[str]) -> list[str]:
        """
        return the list of tokens constituting the corrected tokenized sentence
        """
        words_suggestions: list[WordSuggestions] = []
        for word in words:
            word_suggestions = WordSuggestions(
                word,
                self.__freqdict,
                min_length_for_change=self.__min_length_for_change,
                log=self.__log,
            )
            if self.__log:
                print(word_suggestions)
            words_suggestions.append(word_suggestions)

        windows = self.__get_windows(words_suggestions)
        corrected_words = self.__combine_windows_greedily(words, windows)
        return corrected_words

    def __get_windows(
        self, words_suggestions: list[WordSuggestions], min_window_size=2
    ) -> list[Window]:
        """
        get windows of various sizes (min. window size is 2) and return them sorted descendingly by score

        Flair models are character-based, but we use word as unit here
        """

        min_window_size = min(min_window_size, len(words_suggestions))
        assert min_window_size <= self.__max_window_size

        def words_i_iterator():
            for i in range(len(words_suggestions)):
                for j in range(
                    i + min_window_size,
                    min(i + self.__max_window_size, len(words_suggestions)) + 1,
                ):
                    l_suggested_items = [
                        [item.term for item in suggestions.getSuggestItems()]
                        for suggestions in words_suggestions[i:j]
                    ]

                    if self.__log:
                        print(l_suggested_items)

                    for l_words in itertools.product(*l_suggested_items):
                        if self.__log:
                            print(f"{i}>{j}: {l_words}")

                        yield l_words, i

        l_words_parsed = [" ".join(words) for words, _ in words_i_iterator()]
        scores_per_lm = [
            lm.calculate_perplexity_multi(l_words_parsed) for lm in self.__lms
        ]
        scores = [sum(s) for s in zip(*scores_per_lm)]

        windows: list[Window] = []
        for ij, (words, i) in enumerate(words_i_iterator()):
            score = scores[ij]

            window = Window(
                i,
                words,
                score,
            )
            if self.__log:
                print(window)
            windows.append(window)

        windows = sorted(windows, key=lambda w: w.score, reverse=True)
        if self.__log:
            for window in windows:
                print(window)
        return windows

    def __combine_windows_greedily(
        self, words: list, windows: list[Window]
    ) -> list[str]:
        """
        perform greedy search over the windows sorted descendingly by score and return sequence of words:
        - iterate over windows with largest size, in the order they appear in the list:
          * take highest-scoring window
          * find out next window which does not conflict with the chosen window
          * find out next window which does not conflict with the chosen windows
          * etc.
        - iterate over windows with second largest size, checking potential conflicts with already chosen windows
        - etc.
        the combination of non-conflicting windows results in a sequence of words
        if parts of the sentence are not covered by any chosen window (possible because minimum window size is 2), leave them untouched
        """
        covpos = [""] * len(words)
        for winsize in range(self.__max_window_size, 1, -1):
            filtered = list(filter(lambda x: x.get_size() == winsize, windows))
            for window in sorted(filtered, key=lambda x: x.score):
                conflict = False
                for i in range(window.startpos, window.startpos + winsize):
                    if (
                        covpos[i] != ""
                        and covpos[i] != window.tokens[i - window.startpos]
                    ):
                        conflict = True
                        break
                if conflict:
                    if self.__log:
                        print("conflicting:", window)
                else:
                    if self.__log:
                        print("selected", window)
                    for i in range(window.startpos, window.startpos + winsize):
                        covpos[i] = window.tokens[i - window.startpos]
        if self.__log:
            print(
                "corrected words in sentence, with potential gaps in coverage:",
                list(map(lambda x: "?" if x == "" else x, covpos)),
            )
        corrected_words = list(map(lambda x, y: y if x == "" else x, covpos, words))
        if self.__log:
            print("without gaps in coverage:", corrected_words)

        return corrected_words

    def __detokenize(
        self, line: str, words: list[str], corrected_words: list[str]
    ) -> str:
        if self.__log:
            print(line)
            print(words)
            print(corrected_words)

        line_rest = line[:]
        detokenized = ""

        for word, corrected_word in zip(words, corrected_words):
            if word not in line_rest:
                logger.error(f"{word} not in line")
                raise ValueError(f"{word} not in line")

            spacing, line_rest = line_rest.split(word, 1)

            detokenized += spacing + corrected_word

        detokenized += line_rest
        return detokenized

    def __repr__(self):
        return (
            "CorrectableText(infilename=%r,outfilename=%r,freqdict=%r,modelcacheroot=%r,max_window_size=%r,min_length_for_change=%r,log=%r))"
            % (
                self.__infilename,
                self.__outfilename,
                self.__freqdict,
                self.__modelcacheroot,
                self.__max_window_size,
                self.__min_length_for_change,
                self.__log,
            )
        )

    def __str__(self):
        result = (
            f"correctable text {self.__infilename}, to be treated by applying frequency dictionary {self.__freqdict} and Flair models (cache {self.__modelcacheroot})\n"
            + f"result will be output to file {self.__outfilename}\n"
            + f"maximal size of windows to be corrected is {self.__max_window_size}, tokens shorter than {self.__min_length_for_change} are always left unchanged\n"
            + f"logging is set to {self.__log}"
        )
