import sys
import time
import xml.etree.ElementTree as ET

from symspellpy import SymSpell, Verbosity


class LineBasedTextFile:
    """ file in which each line is a text unit (e.g. sentence) """

    def __init__(self, filename: str, log=False):
        self.__filename = filename
        self.__log = log

    def read(self, stripspaces=False, ignoreemptylines=False) -> list[str]:
        self.__lines = list()
        try:
            infile = open(self.__filename, 'r')
        except Exception as e:
            print(e)
            print("something wrong opening text file for reading, exiting")
        else:
            for line in infile:
                self.__lines.append(line.strip() if stripspaces else line.strip(
                    '\r\n'))  # if STRIPSPACES is true, spaces + newlines are removed)
            infile.close()
        return list(filter(lambda x: x != "", self.__lines)) if ignoreemptylines else self.__lines

    def write(self, lines: list[str]):
        try:
            outfile = open(self.__filename, 'w')
        except Exception as e:
            print(e)
            print("something wrong opening text file for writing, exiting")
        else:
            for line in lines:
                outfile.write(line + "\n")
            outfile.close()
        self.__lines = lines

    @property
    def filename(self) -> str:
        return self.__filename

    @property
    def lines(self) -> list[str]:
        return self.__lines

    def __repr__(self):
        return f"LineBasedTextFile(filename=%r,log=%r)" % (self.__filename, self.__log)

    def __str__(self):
        return f"object which is linked to file {self.__filename} and can read lines from it or writes lines to it; logging is set to {self.__log}"


class PageXMLOutput:
    """
    PageXML file with text areas, lines in text area, and coordinates of areas and lines
    """

    def __init__(self, filename: str, tmpdir="/tmp", log=False):
        self.__filename = filename
        self.__tmpdir = tmpdir
        self.__log = log

    def read_lines(self) -> list[str]:
        self.__lines = []
        try:
            tree = ET.parse(self.__filename)
            root = tree.getroot()
            for elem in root.iter():  # get text lines (we ignore the text area they are part of)
                if elem.tag.endswith('TextLine') and elem[-1][0].text != None:  # tag starts with "{[namespace]}"
                    self.__lines.append(elem[-1][0].text)
                    print(elem[-1][0].text)
        except FileNotFoundError as e:
            print(e)
            print("exiting")
            sys.exit()
        return self.__lines

    def update_lines(self, updatedlines: list[str], outfilename: str, wordspecialsep="__SEP__"):
        try:
            namespaces = {node[0]: node[1] for _, node in ET.iterparse(self.__filename, events=['start-ns'])}
            for key, value in namespaces.items(): ET.register_namespace(key, value)
            tree = ET.parse(self.__filename)
            root = tree.getroot()
            currentregion = None
            regionupdatedlines = []
            wordid = -1
            lineid = -1
            for elem in root.iter():
                if elem.tag.endswith('TextRegion'):
                    if len(regionupdatedlines) > 0:
                        currentregion[-1][0].text = "__CR__\n".join(regionupdatedlines)
                        regionupdatedlines = []
                    currentregion = elem
                elif elem.tag.endswith('TextLine') and elem[-1][0].text != None:
                    lineid += 1
                    wordid = -1
                    elem[-1][0].text = (" ".join(updatedlines[lineid]).replace(wordspecialsep, " "))
                    regionupdatedlines.append((" ".join(updatedlines[lineid]).replace(wordspecialsep, " ")))
                elif elem.tag.endswith('Word'):
                    wordid += 1
                    if wordid >= len(updatedlines[lineid]):
                        print("error! in XML, there are more word blocks than words in the sentence \"" + " ".join(
                            updatedlines[lineid]) + "\"")
                    elem[-1][0].text = updatedlines[lineid][wordid].replace(wordspecialsep, " ")
            if len(regionupdatedlines) > 0:
                currentregion[-1][0].text = "__CR__\n".join(regionupdatedlines)
            tmpoutfilename = self.__tmpdir + "/cr_special_label_" + str(time.time_ns())
            tree.write(tmpoutfilename, encoding='utf-8', xml_declaration=True)
            LineBasedTextFile(outfilename).write(list(
                map(lambda x: (x.replace("__CR__", "&#13;")).replace("?>", " standalone='yes'?>"),
                    LineBasedTextFile(tmpoutfilename).read())))
        except Exception as e:
            print(e)
            print("exiting")
            sys.exit()

    @property
    def filename(self) -> str:
        return self.__filename

    @property
    def lines(self) -> list[str]:
        return self.__lines

    @property
    def tmpdir(self) -> str:
        return self.__tmpdir

    def __repr__(self):
        return f"OCROutput(filename=%r,log=%r)" % (self.__filename, self.__log)

    def __str__(self):
        return f"object that is linked to PageXML file {self.__filename} and can read lines with OCR transcriptions from it or write lines to it; logging is set to {self.__log}"


class NgramDict:
    """
    A dictionary with ngrams that are extracted from a list of words, have a specific length, and are linked to their occurrences (starting word positions).
    The dictionary allows an ngram to be looked up in a fuzzy way in order to retrieve the closest matches.
    """

    def __init__(self, words: list[str], ngramlen=3, max_prop_edit_distance=0.2, max_dictionary_distance_word=2,
                 tmpdir="/tmp", log=False):
        self.__words = words
        self.__ngramlen = ngramlen
        self.__max_prop_edit_distance = max_prop_edit_distance
        self.__max_dictionary_distance_word = max_dictionary_distance_word
        self.__max_dictionary_edit_distance = min(max_dictionary_distance_word * ngramlen,
                                                  6)  # 7 is default prefix length in SymSpell; this length should exceed max_dictionary_edit_distance
        self.__tmpdir = tmpdir
        self.__log = log
        # enable fuzzy lookup
        self.__sym_spell = SymSpell(
            max_dictionary_edit_distance=self.__max_dictionary_edit_distance,
            count_threshold=1  # dummy frequency
        )
        self.__spacesubs = "~"  # we replace space by special character as Symspell does not support entries with spaces
        self.extract_ngrams()

    def extract_ngrams(self):
        """
        Create dictionary and create file enabling fuzzy lookup
        """
        self.__ngrams = dict()
        for i in range(0, len(self.__words) - self.__ngramlen + 1):
            ngram = self.__words[i]
            for j in range(i + 1, i + self.__ngramlen):
                ngram += " " + self.__words[j]
            if ngram not in self.__ngrams:
                self.__ngrams[ngram] = list()
            self.__ngrams[ngram].append(i)
        tmpfile = self.__tmpdir + "/extracted_ngrams_no_spaces_" + str(time.time_ns())
        # format of lines in dictionary file: [word][space][frequency]
        LineBasedTextFile(tmpfile).write(
            list(map(lambda ngram: ngram.replace(" ", self.__spacesubs) + " 1", self.__ngrams.keys())))
        self.__sym_spell.load_dictionary(tmpfile, 0, 1)

    def get_closest_ngrams(self, ngram: str, samelen=True) -> dict[str]:
        """
        Return dictionary with matching ngrams linked to distance
        Matching is character-based; if SAMELEN is FALSE, allow NGRAM to match ngram with a different number of words
        """
        closest = dict()
        for suggestion in self.__sym_spell.lookup(ngram.replace(" ", self.__spacesubs), Verbosity.CLOSEST,
                                                  transfer_casing=False, include_unknown=False,
                                                  max_edit_distance=min(self.__max_dictionary_edit_distance,
                                                                        int(len(
                                                                            ngram) * self.__max_prop_edit_distance))):
            matchingngram = suggestion.term.replace(self.__spacesubs, " ")
            if not samelen or len(matchingngram.split()) == self.__ngramlen:
                closest[matchingngram] = suggestion.distance
        return closest

    def get_ngram_pos(self, ngram) -> list[int]:
        return self.__ngrams.get(ngram, [])

    @property
    def words(self) -> str:
        return self.__words

    @property
    def ngramlen(self) -> int:
        return self.__ngramlen

    @property
    def max_prop_edit_distance_word(self) -> float:
        return self.__max_prop_edit_distance

    @property
    def max_dictionary_distance_word(self) -> int:
        return self.__max_dictionary_distance_word

    @property
    def max_dictionary_edit_distance(self) -> int:
        return self.__max_dictionary_edit_distance

    @property
    def tmpdir(self) -> str:
        return self.__tmpdir

    @property
    def spacesubs(self) -> str:
        return self.__spacesubs

    @property
    def ngrams(self) -> dict[str]:
        return self.__ngrams

    def __repr__(self):
        return f"NgramDict(words=%r, ngramlen=%r, max_prop_edit_distance=%r, max_dictionary_distance_word=%r, tmpdir=%r, log=%r)" % (
            self.__words, self.__ngramlen, self.__max_prop_edit_distance, self.__max_dictionary_distance_word,
            self.__tmpdir, self.__log)

    def __str__(self):
        result = f"ngrams of length {self.__ngramlen} extracted from words {self.__words};\n" + \
                 f"the edit distance of a word sequence wrt a lexicon entry should not exceed\n" + \
                 f"(1) {self.__max_prop_edit_distance * 100}\% of the word sequence \n" + \
                 f"nor\n" + \
                 f"(2) {self.__max_dictionary_distance_word} * {self.__ngramlen} characters;\n" + \
                 f"logging {self.__log}\n"

        result += "\nexample ngrams:"
        maxcount = 5
        for count, ngram in zip(range(len(self.__ngrams)), self.__ngrams):
            if count == maxcount:
                break
            result += "\n" + ngram + " (starting word positions: " + str(self.__ngrams[ngram]) + ")"
        return result


class NgramMatch:
    """
    A match between the occurrence of an ngram in OCR output and the occurrence of another ngram in the corresponding manual transcription,
    and the distance of the match
    """

    def __init__(self, ocrngram: str, ocrpos: int, manngram: str, manpos: int, distance: int, log=False):
        self.__ocrngram = ocrngram
        self.__ocrpos = ocrpos
        self.__manngram = manngram
        self.__manpos = manpos
        self.__distance = distance
        self.__log = log

    @property
    def ocrngram(self) -> str:
        return self.__ocrngram

    @property
    def ocrpos(self) -> int:
        return self.__ocrpos

    @property
    def manngram(self) -> str:
        return self.__manngram

    @property
    def manpos(self) -> int:
        return self.__manpos

    @property
    def distance(self) -> int:
        return self.__distance

    def __repr__(self):
        return f"NgramMatch(ocrngram=%r, ocrpos=%r, manngram=%r, manpos=%r, distance=%r, log=%r)" % (
            self.__ocrngram, self.__ocrpos, self.__manngram, self.__manpos, self.__distance, self.__log)

    def __str__(self):
        return f"match between ngram '{self.__ocrngram}' at position {self.__ocrpos} in OCR output and ngram '{self.__manngram}' at position {self.__manpos} in manual transcription, with distance {self.__distance}\n" + \
            f"logging {self.__log}\n"


class OCRCorrectorManual:
    """
    Finds out corrections to OCR output in a PageXML file based on the ngrams in the corresponding manual transcription
    Adapts the PageXML contents accordingly and writes it to file
    """

    def __init__(self, ocrfilename: str, mantransfilename: str, ngramlen=3, log=False):
        self.__mantransfilename = mantransfilename
        self.__ocrfilename = ocrfilename
        self.__ngramlen = ngramlen
        self.__log = log
        self.__ocrwords = None
        self.__mantranswords = None
        self.__correctedwords = None

    def run(self, ocrupdatefile: str, addorig=False):
        self.__mantranslines, self.__mantranswords, self.__mantranslineswords = self.__get_lineswords(
            self.__mantransfilename)
        self.__manngramdict = NgramDict(self.__mantranswords, ngramlen=self.__ngramlen)
        self.__ocrlines, self.__ocrwords, self.__ocrlineswords = self.__get_lineswords(self.__ocrfilename, pagexml=True)
        self.__ocrngramdict = NgramDict(self.__ocrwords, ngramlen=self.__ngramlen)
        self.__get_ngram_matches()
        self.__get_sets_contiguous_matches()
        self.__wordspecialsep = "__SEP__"
        self.__correct_ocr(addorig=addorig)
        self.__correct_pagexml(ocrupdatefile)

    def __get_lineswords(self, filename: str, pagexml=False) -> tuple[list[str], list[str], [list[list[str]]]]:
        lines = PageXMLOutput(filename).read_lines() if pagexml else LineBasedTextFile(filename).read(
            stripspaces=True, ignoreemptylines=True)
        words = []
        lineswords = []
        for line in lines:
            words.extend(line.split())
            lineswords.append(line.split())
        return lines, words, lineswords

    def __get_ngram_matches(self):
        self.__ngrammatches: set[NgramMatch] = set()
        for ocrngram in self.__ocrngramdict.ngrams:
            matchdict = self.__manngramdict.get_closest_ngrams(ocrngram)
            for ocrpos in self.__ocrngramdict.get_ngram_pos(ocrngram):
                for manngram in matchdict:
                    for manpos in self.__manngramdict.get_ngram_pos(manngram):
                        self.__ngrammatches.add(NgramMatch(ocrngram, ocrpos, manngram, manpos, matchdict[manngram]))

    def __get_sets_contiguous_matches(self, minsetsize=1):
        """
        In a greedy fashion, find out sets of ngram matches which cover a contiguous part of the OCR output
        and a contiguous part of the manual transcription and which contain at least MINSETSIZE matches.
        The contiguous parts should not overlap across sets.
        """
        restmatches = self.__ngrammatches.copy()
        self.__contigmatchsets = list()
        coveredocrpos = [False] * len(self.__ocrwords)
        coveredmanpos = [False] * len(self.__mantranswords)

        while len(restmatches) > 0:
            contigmatchset = set()
            for ngrammatch in sorted(restmatches, key=lambda x: (x.distance, abs(x.ocrpos - x.manpos))):
                if self.__is_compatible(ngrammatch, contigmatchset):
                    contigmatchset.add(ngrammatch)
            for ngrammatch in contigmatchset:
                restmatches.remove(ngrammatch)
                if len(contigmatchset) < minsetsize:
                    break  # merely remove the best match
            if len(contigmatchset) >= minsetsize:
                self.__contigmatchsets.append(contigmatchset)
                for ngrammatch in contigmatchset:
                    for i in range(self.__ngramlen):
                        coveredocrpos[ngrammatch.ocrpos + i] = True
                        coveredmanpos[ngrammatch.manpos + i] = True
                for ngrammatch in restmatches.copy():
                    for i in range(self.__ngramlen):
                        if coveredocrpos[ngrammatch.ocrpos + i] or coveredmanpos[ngrammatch.manpos + i]:
                            restmatches.remove(ngrammatch)
                            break

    def __is_compatible(self, ngrammatch, contigmatchset):
        """
        Set is empty or one of these two conditions applies:
        1) The last words of the OCR ngram occurrence in NGRAMMATCH overlap with the first words
           of the OCR ngram occurrence of one of the ngrams in CONTIGMATCHSET, and the same goes
           for the manual transcription ngrams.
        2) The first words of the OCR ngram occurrence in NGRAMMATCH overlap with the last words
           of the OCR ngram occurrence of one of the ngrams in CONTIGMATCHSET, and the same goes
           for the manual transcription ngrams.
        """
        if len(contigmatchset) == 0:
            return True
        for currmatch in contigmatchset:
            ocroccdist = ngrammatch.ocrpos - currmatch.ocrpos
            manoccdist = ngrammatch.manpos - currmatch.manpos
            if ocroccdist == manoccdist and ocroccdist < self.__ngramlen:
                return True
        return False

    def __correct_ocr(self, leftbracket="[", rightbracket="]", correctionchar="~", addorig=False):
        """
        Loop through all sets of ngram matches covering a contiguous part of the OCR output and a contiguous part
        of the manual transcription and replace words in the OCR output based on the matches in these sets.
        """
        self.__correctedwords = self.__ocrwords.copy()
        coveredocrpos = [False] * len(self.__ocrwords)
        man2ocrpos = [-1] * len(self.__mantranswords)

        for contigmatchset in self.__contigmatchsets:
            for ngrammatch in contigmatchset:
                for i in range(self.__ngramlen):
                    if not coveredocrpos[ngrammatch.ocrpos + i] and self.__correctedwords[ngrammatch.ocrpos + i] != \
                            self.__mantranswords[ngrammatch.manpos + i]:
                        self.__correctedwords[ngrammatch.ocrpos + i] = (
                                (leftbracket + self.__correctedwords[ngrammatch.ocrpos + i] if addorig else '') +
                                correctionchar + self.__mantranswords[ngrammatch.manpos + i] +
                                (rightbracket if addorig else '')
                        )
                    coveredocrpos[ngrammatch.ocrpos + i] = True
                    man2ocrpos[ngrammatch.manpos + i] = ngrammatch.ocrpos + i

        manngramdicts = []
        for i in range(3, 6):
            manngramdicts.append(NgramDict(self.__mantranswords, ngramlen=i, max_prop_edit_distance=0.5))
        for i in range(len(self.__ocrwords)):
            if not coveredocrpos[i]:
                manocrbegpos, manocrendpos = self.__correct_ocr_diffwordnum(self.__correctedwords[i], manngramdicts,
                                                                            man2ocrpos)
                if manocrbegpos == -1:
                    self.__correctedwords[i] = leftbracket + self.__correctedwords[i] + rightbracket
                else:
                    self.__correctedwords[i] = (
                            (leftbracket + self.__correctedwords[i] if addorig else '') +
                            correctionchar + correctionchar + self.__mantranswords[manocrbegpos] +
                            (rightbracket if addorig else '') +
                            self.__wordspecialsep + correctionchar + correctionchar +
                            (self.__wordspecialsep + correctionchar + correctionchar).join(
                                self.__mantranswords[manocrbegpos + 1:manocrendpos + 1])
                    )
                    for j in range(manocrbegpos, manocrendpos + 1):
                        man2ocrpos[j] = i

        i = 0
        while i < len(self.__mantranswords):
            j = i
            while j < len(self.__mantranswords) and man2ocrpos[j] == -1:
                j += 1
            if j > i:
                onlyinmantrans = leftbracket + leftbracket + self.__wordspecialsep.join(
                    self.__mantranswords[i:j]) + rightbracket + rightbracket
                if i == 0:
                    self.__correctedwords[man2ocrpos[j]] = onlyinmantrans + self.__wordspecialsep + \
                                                           self.__correctedwords[man2ocrpos[j]]
                else:
                    self.__correctedwords[man2ocrpos[i - 1]] += self.__wordspecialsep + onlyinmantrans
            i = j + 1

    def __correct_ocr_diffwordnum(self, ocrword, manngramdicts, man2ocrpos):
        for manngramdict in manngramdicts:
            matchdict = manngramdict.get_closest_ngrams(ocrword, samelen=False)
            for manngram in matchdict:
                for manpos in self.__manngramdict.get_ngram_pos(manngram):
                    matching = True
                    for j in range(manpos, manpos + manngramdict.ngramlen):
                        if man2ocrpos[j] > -1:
                            matching = False
                            break
                    if matching:
                        return manpos, manpos + manngramdict.ngramlen - 1
        return -1, -1

    def __correct_pagexml(self, outfilename: str):
        wordcount = 0
        correctedlines = []
        for linewords in self.__ocrlineswords:
            correctedlines.append(self.__correctedwords[wordcount:wordcount + len(linewords)])
            wordcount += len(linewords)
        PageXMLOutput(self.__ocrfilename).update_lines(correctedlines, outfilename,
                                                       wordspecialsep=self.__wordspecialsep)

    @property
    def mantransfilename(self) -> str:
        return self.__mantransfilename

    @property
    def ocrfilename(self) -> str:
        return self.__ocrfilename

    @property
    def ngramlen(self) -> int:
        return self.__ngramlen

    @property
    def mantranslines(self) -> list[str]:
        return self.__mantranslines

    @property
    def mantranswords(self) -> list[str]:
        return self.__mantranswords

    @property
    def mantranslineswords(self) -> list[str]:
        return self.__mantranslineswords

    @property
    def manngramdict(self) -> dict[str]:
        return self.__manngramdict

    @property
    def ocrlines(self) -> list[str]:
        return self.__ocrlines

    @property
    def ocrwords(self) -> list[str]:
        return self.__ocrwords

    @property
    def ocrlineswords(self) -> list[list[str]]:
        return self.__ocrlineswords

    @property
    def ocrngramdict(self) -> dict[str]:
        return self.__ocrngramdict

    @property
    def ngrammatches(self) -> set:
        return self.__ngrammatches

    @property
    def contigmatchsets(self) -> set:
        return self.__contigmatchsets

    @property
    def correctedwords(self) -> list[str]:
        return self.__correctedwords

    def __repr__(self):
        return f"OCRCorrectorOld(mantransfilename=%r, ocrfilename=%r, ngramlen=%r, log=%r)" % (
            self.__mantransfilename, self.__ocrfilename, self.__ngramlen, self.__log)

    def __str__(self):
        result = f"OCR corrector running on PageXML file {self.__ocrfilename} and manual transcription in {self.__mantransfilename}\n" + \
                 f"comparison is based on ngram length {self.__ngramlen}\n" + \
                 f"logging set to {self.__log}"

        maxcount = 30
        if self.__ocrwords is not None:
            result += "\nOCR words: " + str(self.__ocrwords[0:maxcount])
        if self.__mantranswords is not None:
            result += "\nmanual transcription words: " + str(self.__mantranswords[0:maxcount])
        if self.__correctedwords is not None:
            result += "\ncorrected OCR words: " + str(self.__correctedwords[0:maxcount])

        return result


if __name__ == "__main__":
    ocroutfile, mantrans, outfile = sys.argv[1:4]
    OCRCorrectorManual(ocroutfile, mantrans).run(outfile, len(sys.argv) == 5)
