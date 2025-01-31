import sys
import time
import xml.etree.ElementTree as ET
from Levenshtein import distance, ratio  # pip install levenshtein
from symspellpy import SymSpell, Verbosity
import copy


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

    def write(self, text):
        """ write string or list of lines """
        if type(text) == str:
            lines = list(text.split("\n"))
        else:
            lines = text
        if self.__log: print(lines)

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
    PageXML file with text areas, lines in text area, and coordinates of areas and lines; possibly also with word areas
    a textregion may or may not end in a TextEquiv element
    """

    def __init__(self, filename: str, tmpdir="/tmp", log=False):
        self.__filename = filename
        self.__tmpdir = tmpdir
        self.__log = log

    def read_lines(self) -> list[str]:
        self.__lines = []
        # get text lines (we ignore the text area they are part of)
        try:
            tree = ET.parse(self.__filename)
            for lineelt in self.__get_desc(tree.getroot(), 'TextLine', direct=False):
                equiv = self.__get_desc(lineelt, 'TextEquiv')[0]
                text = self.__get_desc(equiv, 'Unicode')[
                    0].text  # Unicode may have a sister PlainText, but we ignore it
                if text != None: self.__lines.append(text)
        except FileNotFoundError as e:
            print(e)
            print("exiting")
            sys.exit()
        return self.__lines

    def __get_desc(self, elem: ET.Element, tagname: str, direct=True) -> ET.Element:
        """ get descendants, possibly only the children """
        namespace = elem.tag.split('}')[0][1:]
        desc = list()
        for othelem in (elem.findall if direct else elem.iter)('{' + namespace + '}' + tagname):
            if othelem.tag == "{" + namespace + '}' + tagname:
                desc.append(othelem)
        return desc

    def update_lines(self, updatedlines: list[str], outfilename: str):
        """ Replace TextLine elements by items in UPDATELINES
            If TextRegion has no TextEquiv element, create one and add concatenated lines of the region to it; if it has, replace the text of the original TextEquiv element
            It there are Word elements, remove them, as they are difficult to synchronise with changes to TextLine elements (e.g. when a line contains additional words after correction)
            If there are PlainText elements, remove them
        """
        try:
            namespaces = {node[0]: node[1] for _, node in ET.iterparse(self.__filename, events=['start-ns'])}
            for key, value in namespaces.items(): ET.register_namespace(key, value)
            tree = ET.parse(self.__filename)
            root = tree.getroot()
            lineid = 0
            for lineelt in self.__get_desc(root, 'TextLine', direct=False):
                equiv = self.__get_desc(lineelt, 'TextEquiv')[0]
                if self.__get_desc(equiv, 'Unicode')[0].text != None:
                    self.__get_desc(equiv, 'Unicode')[0].text = updatedlines[lineid]
                    lineid += 1
                plaintextelts = self.__get_desc(equiv, 'PlainText')
                if len(plaintextelts) > 0:
                    equiv.remove(plaintextelts[0])
                for wordelt in self.__get_desc(lineelt, 'Word'):
                    lineelt.remove(wordelt)
            for region in self.__get_desc(root, 'TextRegion', direct=False):
                regionupdatedlines = []
                for lineelt in self.__get_desc(region, 'TextLine'):
                    equiv = self.__get_desc(lineelt, 'TextEquiv')[0]
                    text = self.__get_desc(equiv, 'Unicode')[0].text
                    if text != None: regionupdatedlines.append(text)
                equivs = self.__get_desc(region, 'TextEquiv')
                unicodeelt = ET.Element('Unicode') if len(equivs) == 0 else self.__get_desc(equivs[0], "Unicode")[0]
                unicodeelt.text = "__CR__\n".join(regionupdatedlines)
                if len(equivs) == 0:
                    equiv = ET.Element('TextEquiv')
                    equiv.append(unicodeelt)
                    region.append(equiv)
                if self.__log: print("regionupdatedlines", regionupdatedlines)
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
        return f"OCROutput(filename=%r,tmpdir=%r,log=%r)" % (self.__filename, self.__tmpdir, self.__log)

    def __str__(self):
        return f"object that is linked to PageXML file {self.__filename} and can read lines with OCR transcriptions from it or write lines to it; " + \
            f"uses temporary directory {self.__tmpdir}; logging is set to {self.__log}"


class NgramDict:
    """
    A dictionary with ngrams that are extracted from a list of words, have a specific length, and are linked to their occurrences (starting word positions).
    The dictionary allows an ngram to be looked up in a fuzzy way in order to retrieve the closest matches.
    """

    def __init__(self, words: list[str], ngramlen=3, maxdistprop=0.5, maxdistword=5, minwordsim=0.3,
                 tmpdir="/tmp", log=False):
        self.__words = words
        self.__ngramlen = ngramlen
        self.__maxdistprop = maxdistprop
        self.__maxdistword = maxdistword
        self.__minwordsim = minwordsim
        self.__max_dictionary_edit_distance = min(maxdistword * ngramlen, 10)
        self.__tmpdir = tmpdir
        self.__log = log
        # enable fuzzy lookup
        if self.__log: print(self.__max_dictionary_edit_distance)
        self.__sym_spell = SymSpell(
            max_dictionary_edit_distance=self.__max_dictionary_edit_distance,
            prefix_length=self.__max_dictionary_edit_distance + 1,
            # prefix length should exceed max_dictionary_edit_distance
            count_threshold=1  # dummy frequency
        )
        self.__spacesubs = "~"  # we replace space by special character as Symspell does not support entries with spaces
        self.__extract_ngrams()

    def __extract_ngrams(self):
        """
        Create dictionary and create file enabling fuzzy lookup
        """
        self.__ngrams = dict()  # map ngram to list of occurrences
        for i in range(0, len(self.__words) - self.__ngramlen + 1):
            ngram = self.__words[i]
            for j in range(i + 1, i + self.__ngramlen):
                ngram += " " + self.__words[j]
            if self.__log: print(ngram)
            if ngram not in self.__ngrams:
                self.__ngrams[ngram] = list()
            self.__ngrams[ngram].append(i)
        if self.__log:
            for ngram in self.__ngrams:
                print(" " + ngram)
        tmpfile = self.__tmpdir + "/extracted_ngrams_no_spaces_" + str(time.time_ns())
        # format of lines in dictionary file: [word][space][frequency]
        LineBasedTextFile(tmpfile).write(
            list(map(lambda ngram: ngram.replace(" ", self.__spacesubs) + " 1", self.__ngrams.keys())))
        if self.__log: print(tmpfile)
        self.__sym_spell.load_dictionary(tmpfile, 0, 1)

    def get_closest_ngrams(self, ngram: str, samelen=True) -> dict[str]:
        """
        Return dictionary with matching ngrams linked to distance
        Matching is character-based; if SAMELEN is FALSE, allow NGRAM to match ngram with a different number of words
        """
        words = ngram.split()
        closest = dict()
        maxdistdict = min(self.__max_dictionary_edit_distance, int(len(
            ngram) * self.__maxdistprop))  # if we have a short ngram, edit distance should not be the maximal one allowed
        if self.__log: print("looking up", ngram, self.__max_dictionary_edit_distance, self.__maxdistprop,
                             self.__maxdistword, maxdistdict)
        for suggestion in self.__sym_spell.lookup(ngram.replace(" ", self.__spacesubs), Verbosity.CLOSEST,
                                                  transfer_casing=False, include_unknown=False,
                                                  max_edit_distance=maxdistdict):
            matchingngram = suggestion.term.replace(self.__spacesubs, " ")
            accept = True
            if samelen and len(matchingngram.split()) == self.__ngramlen:
                matchingwords = matchingngram.split()
                accept = True
                for i in range(self.__ngramlen):
                    # Levenshtein ratio
                    # 1 - (indel distance / (len1 + len2)) (indel distance is minimum number of insertions and deletions required to change one sequence into the other
                    if ratio(words[i], matchingwords[i]) < self.__minwordsim:
                        accept = False
                        break
            if accept: closest[matchingngram] = suggestion.distance
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
    def maxdistprop(self) -> float:
        return self.__maxdistprop

    @property
    def maxdistword(self) -> int:
        return self.__maxdistword

    @property
    def max_dictionary_edit_distance(self) -> int:
        return self.__max_dictionary_edit_distance

    @property
    def minwordsim(self) -> float:
        return self.__minwordsim

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
        return f"NgramDict(words=%r, ngramlen=%r, maxdistprop=%r, maxdistword=%r, minwordsim-%r, tmpdir=%r, log=%r)" % (
            self.__words, self.__ngramlen, self.__maxdistprop, self.__maxdistword, self.__minwordsim,
            self.__tmpdir, self.__log)

    def __str__(self):
        result = f"ngrams of length {self.__ngramlen} extracted from words {self.__words};\n" + \
                 f"the edit distance of a word sequence wrt a lexicon entry should not exceed\n" + \
                 f"(1) {self.__maxdistprop * 100}\% of the word sequence, \n" + \
                 f"(2) {self.__maxdistword} * {self.__ngramlen} characters,\n" + \
                 f"nor\n" + \
                 f"(3) an absolute value of 10\n" + \
                 f"if word sequence and lexicon entry contain same number of words, words at same position should have Levenshtein similarity of at least {self.__minwordsim}\n" + \
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
        return f"match between ngram '{self.__ocrngram}' at position {self.__ocrpos} in OCR output and ngram '{self.__manngram}' " + \
            f"at position {self.__manpos} in manual transcription, with distance {self.__distance}\n" + \
            f"logging {self.__log}\n"


class OCRCorrectorManual:
    """
    Finds out corrections to OCR output in a PageXML file based on the ngrams in the corresponding manual transcription
    Adapts the PageXML contents accordingly and writes it to file
    """

    def __init__(self, ocrfilename: str, manfilename: str, ngramlen=3, maxdistprop=0.5, maxdistword=5, minwordsim=0.5,
                 minwordsimstrong=0.6, maxngrammulti=3, maxdistunlinked=3, xmllogchanges=0, logfile="", log=False):
        self.__ocrfilename = ocrfilename
        self.__manfilename = manfilename
        self.__ngramlen = ngramlen
        self.__maxdistprop = maxdistprop
        self.__maxdistword = maxdistword
        self.__minwordsim = minwordsim
        self.__minwordsimstrong = minwordsimstrong
        self.__maxngrammulti = maxngrammulti
        self.__maxdistunlinked = maxdistunlinked
        self.__xmllogchanges = xmllogchanges
        self.__logfile = logfile
        self.__log = log
        self.__ocrlines: list[str] = None
        self.__ocrwords: list[str] = None
        self.__ocrlineswords: list[list[str]] = None
        self.__manlines: list[str] = None
        self.__manwords: list[str] = None
        self.__manlineswords: list[list[str]] = None
        self.__correctedlines: list[str] = None
        self.__wordmapping: list[list[tuple[int, int]]] = None  # final word mapping
        self.__tmpwordmappings: dict() = None  # keys: "1 contigmatchsets", "2 multiword", "3 strong", "4 short"

    def run(self, ocrupdatefile: str):
        self.__ocrlines, self.__ocrwords, self.__ocrlineswords = self.__get_lineswords(self.__ocrfilename, pagexml=True)
        self.__manlines, self.__manwords, self.__manlineswords = self.__get_lineswords(self.__manfilename)
        self.__get_ngram_matches()
        self.__get_sets_contiguous_matches()
        self.__map_ocrwords_to_manual()
        self.__correct_lines()
        PageXMLOutput(self.__ocrfilename).update_lines(self.__correctedlines, ocrupdatefile)
        if self.__logfile != "":
            LineBasedTextFile(self.__logfile).write(
                f"parameters:\nocrfilename {self.__ocrfilename}\nmanfilename {self.__manfilename}\nngramlen {self.__ngramlen}\n" + \
                f"maxdistprop {self.__maxdistprop}\nmaxdistword {self.__maxdistword}\nminwordsim {self.__minwordsim}\n" + \
                f"minwordsimstrong {self.__minwordsimstrong}\nmaxngrammulti {self.__maxngrammulti}\nmaxdistunlinked {self.__maxdistunlinked}\n" + \
                f"xmllogchanges {self.__xmllogchanges}\n\n" + \
                self.__get_texts_mappings_pretty_print())

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
        """ get all matches between ngrams in OCR/HTR output and manual transcription that satisfy the closeness criteria imposed by ngram dictionary """
        self.__ocrngramdict = NgramDict(self.__ocrwords, ngramlen=self.__ngramlen, maxdistprop=self.__maxdistprop,
                                        maxdistword=self.__maxdistword, minwordsim=self.__minwordsim)
        self.__manngramdict = NgramDict(self.__manwords, ngramlen=self.__ngramlen, maxdistprop=self.__maxdistprop,
                                        maxdistword=self.__maxdistword, minwordsim=self.__minwordsim)
        self.__ngrammatches: set[NgramMatch] = set()
        for ocrngram in self.__ocrngramdict.ngrams:
            matchdict = self.__manngramdict.get_closest_ngrams(ocrngram)
            for ocrpos in self.__ocrngramdict.get_ngram_pos(
                    ocrngram):  # look at each occurrence of this ngram in OCR output
                for manngram in matchdict:
                    for manpos in self.__manngramdict.get_ngram_pos(manngram):
                        self.__ngrammatches.add(NgramMatch(ocrngram, ocrpos, manngram, manpos, matchdict[manngram]))
        if self.__log:
            for ngrammatch in self.__ngrammatches:
                print(ngrammatch)

    def __get_sets_contiguous_matches(self, minsetsize=3):
        """
        In a greedy fashion, find out sets of ngram matches which cover a contiguous part of the OCR output
        and a contiguous part of the manual transcription and which contain at least MINSETSIZE matches.
        The contiguous parts should not overlap across sets.
        """
        restmatches = self.__ngrammatches.copy()
        self.__contigmatchsets = list()
        coveredocrpos = [False] * len(self.__ocrwords)
        coveredmanpos = [False] * len(self.__manwords)
        while len(restmatches) > 0:
            contigmatchset: set[NgramMatch] = set()
            spanocrpos, spanmanpos = -1, -1
            spanlen = 0
            while (True):
                prevspanlen = spanlen
                for ngrammatch in sorted(restmatches, key=lambda x: (x.distance,
                                                                     abs(x.ocrpos - x.manpos))):  # ignores length of ngrams in terms of chars / words; should it?
                    if self.__log: print("test:\n" + str(ngrammatch))
                    if spanocrpos == -1:
                        spanocrpos, spanmanpos = ngrammatch.ocrpos, ngrammatch.manpos
                        spanlen = self.__ngramlen
                    elif ngrammatch.ocrpos == spanocrpos - 1 and ngrammatch.manpos == spanmanpos - 1:
                        spanocrpos -= 1
                        spanmanpos -= 1
                        spanlen += 1
                    elif ngrammatch.ocrpos + self.__ngramlen == spanocrpos + spanlen and ngrammatch.manpos + self.__ngramlen == spanmanpos + spanlen:
                        spanlen += 1
                    else:
                        continue
                    contigmatchset.add(ngrammatch)
                    if self.__log: print("adding:\n" + str(ngrammatch))
                if spanlen == prevspanlen: break
            if self.__log: print("finished loop")
            for ngrammatch in contigmatchset:
                restmatches.remove(ngrammatch)
                if self.__log: print("removing\n", str(ngrammatch))
                if len(contigmatchset) < minsetsize: break  # merely remove the best match
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
                            if self.__log: print("--- removing\n", str(ngrammatch))
                            break

    def __map_ocrwords_to_manual(self):
        """ map each word in OCR/HTR output to a sequence of one or more words in manual transcription, and vice versa
            if a word is mapped to a single word, the words are identical or different
            some words in both text may remain unlinked
            (not covered: map multiple words to multiple words - could be helpful to deal with unlinked words?)
        """
        self.__wordmapping = [[(-1, -1)] * len(self.__ocrwords),
                              # [ beginning position in manual transcription, ending position ] (typically identical positions)
                              [(-1, -1)] * len(self.__manwords)]  # [ beginning position in output, ending position ]

        self.__tmpwordmappings = dict()

        # map words to words
        for contigmatchset in self.__contigmatchsets:
            for ngrammatch in contigmatchset:
                if self.__log: print("ngrammatch\n", str(ngrammatch))
                for i in range(self.__ngramlen):
                    self.__wordmapping[0][ngrammatch.ocrpos + i] = (ngrammatch.manpos + i, ngrammatch.manpos + i)
                    self.__wordmapping[1][ngrammatch.manpos + i] = (ngrammatch.ocrpos + i, ngrammatch.ocrpos + i)
        self.__tmpwordmappings["1 contigmatchsets"] = copy.deepcopy(self.__wordmapping)

        # update mapping
        self.__get_multiword_matches()  # link one word to multiple words
        self.__tmpwordmappings["2 multiword"] = copy.deepcopy(self.__wordmapping)

        self.__get_strongly_similar_matches()  # link words in highly similar sequences in which words at same position have strong match
        self.__tmpwordmappings["3 strong"] = copy.deepcopy(self.__wordmapping)

        self.__fill_short_unlinked()  # in unlinked sequences with identical length, link words at same position, whatever their similarity
        self.__tmpwordmappings["4 short"] = copy.deepcopy(self.__wordmapping)

    def __get_strongly_similar_matches(self):
        """ in each pair of unlinked sequences, detect a pair of word sequences for which the following goes:
            (a) they have the same number of words
            (b) the word at position X in one sequence is strongly similar to the word at position X in the other sequence
            and
            (c) the first word of each sequence starts before or at position MAXDISTUNLINKED (0-based) in sequence

            based on these word sequences, the word mapping is modified

            if more than one word sequence pair is found in a pair of unlinked sequences, we only keep one; as we apply the above procedure iteratively on all pairs,
            such additional word sequence pairs may be detected in subsequent iterations; we stop iterating until no more changes are made to the word mapping
        """
        if self.__log: print(self.__get_unlinked_sequence_pairs())
        while (True):
            modifiedmapping = False
            for sequencepair in self.__get_unlinked_sequence_pairs():
                for i in range(sequencepair[0], min(sequencepair[0] + self.__maxdistunlinked, sequencepair[1]) + 1):
                    matchlen = 0
                    for j in range(sequencepair[2], sequencepair[3] + 1):
                        # Levenshtein ratio
                        if ratio(self.__ocrwords[i + matchlen], self.__manwords[j]) >= self.__minwordsimstrong:
                            self.__wordmapping[0][i + matchlen] = (j, j)
                            self.__wordmapping[1][j] = (i + matchlen, i + matchlen)
                            matchlen += 1
                            modifiedmapping = True
                            if i + matchlen == sequencepair[0] + sequencepair[1]: break
                        elif matchlen > 0:  # we found match and cannot extend it any more; we ignore any other matches
                            break
                        elif j == self.__maxdistunlinked:
                            break
                    if matchlen: break
            if not modifiedmapping: break

    def __get_multiword_matches(self):
        """ in each pair of unlinked sequences, detect an OCR/HTR word for which the following goes:
            (a) it starts before or at position MAXDISTUNLINKED in sequence
            (b) it is strongly similar to a multiword sequence starting before or at position MAXDISTUNLINKED in manual transcription sequence
            and
            (c) the similarity to the multiword sequence is larger than that with a specific word in the multiword
            (e.g. "Demokravie" matches with "Demokratie is" but matches more with "Demokratie")

            if a match is found, the word mapping is modified

            if more than one word with the above properties is found in a pair of unlinked sequences, we only keep one; as we apply the above procedure iteratively on all pairs,
            such additional words may be detected in subsequent iterations; we stop iterating until no more changes are made to the word mapping
        """
        if self.__log: print(self.__get_unlinked_sequence_pairs())
        wordlists = [self.__ocrwords, self.__manwords]
        while (True):
            modifiedmapping = False
            unlinkedsequences = self.__get_unlinked_sequence_pairs()
            if self.__log: print("multi", unlinkedsequences)
            for i in range(2):
                for sequencepair in unlinkedsequences:
                    begpos1, endpos1, begpos2, endpos2 = sequencepair if i == 0 else [*sequencepair[2:4],
                                                                                      *sequencepair[0:2]]
                    for pos1 in range(begpos1, min(begpos1 + self.__maxdistunlinked, endpos1) + 1):
                        for pos2 in range(begpos2,
                                          min(begpos2 + self.__maxdistunlinked, endpos2)):  # start with bigrams
                            singlesim = ratio(wordlists[i][pos1], wordlists[1 - i][pos2])
                            foundmatch = False
                            for ngramlen in range(2, self.__maxngrammulti + 1):
                                multisim = ratio(wordlists[i][pos1], " ".join(wordlists[1 - i][pos2:pos2 + ngramlen]))
                                if self.__log: print(pos1, pos2, ngramlen, len(self.__wordmapping[i]), "1",
                                                     wordlists[i][pos1], "2",
                                                     " ".join(wordlists[1 - i][pos2:pos2 + ngramlen]), multisim)
                                if multisim >= self.__minwordsimstrong and multisim > singlesim:
                                    self.__wordmapping[i][pos1] = (pos2, pos2 + ngramlen - 1)
                                    for j in range(pos2, pos2 + ngramlen): self.__wordmapping[1 - i][j] = (pos1, pos1)
                                    modifiedmapping = True
                                    foundmatch = True
                                    break
                                if foundmatch or begpos2 + ngramlen >= endpos2 + 1: break
                            if foundmatch: break
            if not modifiedmapping: break

    def __fill_short_unlinked(self):
        """ if unlinked sequences have the same length, and it does not exceed MAXDISTUNLINKED, link words at same position in sequence, regardless of their similarity """
        if self.__log: print(self.__get_unlinked_sequence_pairs())
        for begpos1, endpos1, begpos2, endpos2 in self.__get_unlinked_sequence_pairs():
            if endpos1 - begpos1 == endpos2 - begpos2 and endpos1 - begpos1 <= self.__maxdistunlinked:
                for i in range(endpos1 - begpos1 + 1):
                    self.__wordmapping[0][begpos1 + i] = (begpos2 + i, begpos2 + i)
                    self.__wordmapping[1][begpos2 + i] = (begpos1 + i, begpos1 + i)

    def __get_unlinked_sequence_pairs(self):
        """ sequences starting at beginning of output/transcription or just after positions linked to each other,
            and ending at end of output/transcription of just before positions linked to each other
        """
        sequences: list[tuple(int, int, int,
                              int)] = []  # [start position of OCR sequence, end position, start position of manual transcription, end position]
        gapocrstart = -1  # first unlinked position in sequence of unlinked positions; -1 = we processed the previous such sequence (or did not find one yet)
        for i in range(len(self.__wordmapping[0]) + 1):
            if i < len(self.__wordmapping[0]) and self.__wordmapping[0][i] == (
            -1, -1):  # detect start of unlinked sequence in OCR/HTR output
                if i == 0 or self.__wordmapping[0][i - 1] != (-1, -1): gapocrstart = i
            elif gapocrstart != -1:  # are we at position following unlinked sequence (or end of output, and output follows such a sequence)?
                if i == len(self.__wordmapping[0]) or gapocrstart == 0 or self.__wordmapping[0][i][0] > \
                        self.__wordmapping[0][gapocrstart - 1][0]:
                    # check whether all positions in manual transcription sequence are unlinked
                    gapmanstart = 0 if gapocrstart == 0 else self.__wordmapping[0][gapocrstart - 1][1] + 1
                    gapmanend = len(self.__wordmapping[1]) - 1 if i == len(self.__wordmapping[0]) else \
                    self.__wordmapping[0][i][0] - 1
                    if gapmanstart < gapmanend + 1:  # gap may be empty
                        manallunlinked = True
                        for j in range(gapmanstart, gapmanend + 1):
                            if self.__wordmapping[1][j] != (-1, -1):
                                manallunlinked = False
                                break
                        if manallunlinked: sequences.append((gapocrstart, i - 1, gapmanstart, gapmanend))
                gapocrstart = -1
        return sequences

    def __correct_lines(self, leftbracket="[", rightbracket="]", correctionchar="~"):
        """
        scenarios:
        1) if word is linked to other word and they are identical: nothing happens
        2) if word is linked to other word and they are different, or if word is linked to multiple words: replace word by other word or by word sequence
        3) if all words in a sequence are linked to one specific word in the other text: replace word sequence by that word
        4) if word is only present in the OCR/HTR output: remove word (note that removal of words may lead to empty lines)
        5) if word sequence is only present in the manual transcription:
           add word sequence before/after the (corrected version of) word in the output (and hence possibly before/after a removed word), and therefore on the same line:
           * if word sequence is the start of the manual transcription: before the first word in the OCR output
           * if sequence follows word in manual transcription that is linked to an OCR output word: after that OCR output word

        if XMLLOGCHANGES is 1, prepend CORRECTIONCHAR to each replacing / added word in scenario 2 to 5 (in scenario 4, this will lead to a sole character, as word is removed)
        if XMLLOGCHANGES is 2, also prepend LEFTBRACKET + original word or word sequence + RIGHTBRACKET for scenario 2 to 4; for scenario 5, prepend LEFTBRACKET + RIGHTBRACKET
        """
        ocrpos2manunlinked = self.__map_ocrpos_to_manunlinked()  # preprocessing for coping with scenario 5
        if self.__log: print("ocrpos2manunlinked", ocrpos2manunlinked)
        self.__correctedlines = []
        ocrwordid = 0  # keep track of position in OCRWORDS, i.e. independent from line in which word occurs
        for line in self.__ocrlineswords:
            if self.__log: print(line)
            self.__correctedlines.append("")
            for word in line:
                manbegpos, manendpos = self.__wordmapping[0][ocrwordid]
                # scenario 4
                if manbegpos == -1:
                    correctedwords = ""
                # scenario 1 or 2 (OCR word is linked to word or word sequence), or first word of OCR sequence is linked (scenario 3)
                elif ocrwordid == 0 or self.__wordmapping[0][ocrwordid] != self.__wordmapping[0][ocrwordid - 1]:
                    correctedwords = " ".join(self.__manwords[manbegpos:manendpos + 1])
                else:  # second and subsequent words of OCR sequence (scenario 3)
                    ocrwordid += 1
                    continue
                if self.__log: print(correctedwords)
                origwords = [word]
                for i in range(ocrwordid + 1, len(self.__ocrwords)):
                    if self.__wordmapping[0][i] != (-1, -1) and self.__wordmapping[0][i] == self.__wordmapping[0][
                        ocrwordid]:
                        origwords.append(self.__ocrwords[i])  # scenario 3
                    else:
                        break
                if self.__log: print(word, correctedwords, origwords)
                if self.__xmllogchanges > 0 and (len(origwords) > 1 or correctedwords != word):
                    correctedwords = (leftbracket + " ".join(
                        origwords) + rightbracket if self.__xmllogchanges == 2 else "") + \
                                     (correctionchar if correctedwords == "" else " ".join(
                                         list(map(lambda x: correctionchar + x, correctedwords.split()))))
                # scenario 5
                manatstart = ocrwordid == 0 and -1 in ocrpos2manunlinked
                if manatstart or ocrwordid in ocrpos2manunlinked:
                    manbegpos, manendpos = ocrpos2manunlinked[-1 if manatstart else ocrwordid]
                    if self.__log: print(manbegpos, manendpos, self.__manwords[manbegpos:manendpos + 1])
                    for manword in self.__manwords[manendpos:manbegpos - 1:-1] if manatstart else self.__manwords[
                                                                                                  manbegpos:manendpos + 1]:
                        wordadded = (leftbracket + rightbracket if self.__xmllogchanges == 2 else "") + (
                            correctionchar if self.__xmllogchanges > 0 else "") + manword
                        if manatstart:
                            correctedwords = wordadded + ("" if correctedwords == "" else " " + correctedwords)
                        else:
                            correctedwords += ("" if correctedwords == "" else " ") + wordadded
                self.__correctedlines[-1] += ("" if self.__correctedlines[
                                                        -1] == "" or correctedwords == "" else " ") + correctedwords
                if self.__log: print(self.__correctedlines[-1])
                ocrwordid += 1

    def __map_ocrpos_to_manunlinked(self) -> dict:
        """ map OCR positions >= -1 to 2-tuples (1) start position of sequence in manual transcription to add before or after OCR position, (2) end position of sequence
            (-1 is virtual position before start of output/transcription)
        """
        if self.__log: print(self.__get_unlinked_sequence_pairs())
        ocrpos2manunlinked = dict()
        manposfound = set()
        self.__manorphannum = 0  # number of words in manual transcription that are unlinked and which do not "substitute" an OCR/HTR word
        for ocrbegpos, ocrendpos, manbegpos, manendpos in self.__get_unlinked_sequence_pairs():
            if self.__log: print(ocrbegpos, ocrendpos, manbegpos, manendpos)
            # map each OCR position to corresponding position;
            # if there are less OCR positions than manual transcription positions, map last OCR position to a range of positions (i.e. we add "orphan" words from manual transcription)
            # if there are more OCR positions than manual transcription positions, ignore the last OCR positions
            for i in range(ocrbegpos, ocrendpos + 1):
                if manbegpos + i - ocrbegpos > manendpos: break
                ocrpos2manunlinked[i] = (manbegpos + i - ocrbegpos,
                                         manendpos if i == ocrendpos and manendpos - manbegpos > ocrendpos - ocrbegpos else manbegpos + i - ocrbegpos)
                self.__manorphannum += ocrpos2manunlinked[i][1] - ocrpos2manunlinked[i][0]
                manposfound = manposfound.union(set(range(ocrpos2manunlinked[i][0], ocrpos2manunlinked[i][1] + 1)))
        if self.__log: print("ocrpos2manunlinked", ocrpos2manunlinked)
        # if we have manual transcription positions that are not part of unlinked sequence pairs, we add them all before/after following/preceding OCR position
        for i in range(len(self.__manwords)):
            if not i in manposfound and self.__wordmapping[1][i] == (-1, -1):
                if i == 0 or self.__wordmapping[1][i - 1] != (-1, -1):
                    ocrpos = -1 if i == 0 else self.__wordmapping[1][i - 1][0]
                    ocrpos2manunlinked[ocrpos] = [i,
                                                  i]  # update second element below, if sequence contains multiple words
                else:
                    ocrpos2manunlinked[ocrpos][1] = i
                    self.__manorphannum += 1
        if self.__log: print("ocrpos2manunlinked", ocrpos2manunlinked)
        return ocrpos2manunlinked

    def __get_texts_mappings_pretty_print(self, fromocr=True, maxcount=-1) -> str:
        if self.__ocrwords == None: return

        def get_first_n(elts: list[str], n: int) -> str:
            result = "\n".join(elts[0:len(elts) if n == -1 else n])
            if n != -1 and n < len(elts) - 1: result += "\n..."
            return result

        def side_by_side(text1, text2, withlinenum=False) -> str:
            lines1, lines2 = [text1.split("\n"), text2.split("\n")] if type(text1) == str else [text1, text2]
            maxlen1 = 0
            for line in lines1: maxlen1 = max(maxlen1, len(line))
            maxlen2 = 0
            for line in lines2: maxlen2 = max(maxlen2, len(line))
            prefixlen1, prefixlen2 = len(str(len(lines1))), len(str(len(lines2)))
            maxlen1 += prefixlen1
            maxlen1 += prefixlen2
            result = ""
            for i in range(max(len(lines1), len(lines2))):
                line1 = (f"{i:>{prefixlen1}} " if withlinenum else "") + lines1[i] if i < len(lines1) else ""
                line2 = (f"{i:>{prefixlen2}} " if withlinenum else "") + lines2[i] if i < len(lines2) else ""
                result += ("" if i == 0 else "\n") + f"{line1:<{maxlen1}} {line2:<{maxlen2}}"
            return result

        pretty_print = "*** OCR / manual lines:\n" + side_by_side(get_first_n(self.__ocrlines, maxcount),
                                                                  get_first_n(self.__manlines, maxcount)) + \
                       "\n\n*** OCR/manual words:\n" + side_by_side(self.__ocrwords, self.__manwords,
                                                                    withlinenum=True) + \
                       "\n\n*** ngram matches:\n" + get_first_n(list(map(lambda x: str(x), self.__ngrammatches)),
                                                                maxcount) + \
                       "\n\n*** word mappings at various steps:"

        wordlists = [self.__ocrwords, self.__manwords]
        prevmapping = None
        for mappingtype in sorted(self.__tmpwordmappings):
            pretty_print += f"\n\n***   {mappingtype}\n"
            mapping = self.__tmpwordmappings[mappingtype]
            lines = [[], []]
            for i in range(2):
                for j in range(len(mapping[i])):
                    if maxcount != -1 and j == maxcount: break
                    topos = "[" + str(mapping[i][j][0]) + (
                        "" if mapping[i][j][0] == mapping[i][j][1] else ", " + str(mapping[i][j][1])) + "]"
                    lines[i].append(("[NEW] " if prevmapping != None and prevmapping[i][j] == (-1, -1) and mapping[i][
                        j] != (-1, -1) else "") + \
                                    f"{wordlists[i][j]} -> {topos}" + \
                                    ("" if mapping[i][j][0] == -1 else " " + " ".join(
                                        wordlists[1 - i][mapping[i][j][0]:mapping[i][j][1] + 1])))
            pretty_print += side_by_side(*lines, withlinenum=True)
            prevmapping = mapping

        colwidth = 60
        pretty_print += "\n\n*** manual transcription vs. original OCR/HTR output vs. corrected version:\n" + \
                        "\n".join(list(map(lambda x: x + "\n" + ("=" * len(x)),
                                           side_by_side(get_first_n(self.__manlines, maxcount),
                                                        side_by_side(get_first_n(self.__ocrlines, maxcount),
                                                                     get_first_n(self.__correctedlines,
                                                                                 maxcount))).split("\n"))))

        ocrunlinked = len(list(filter(lambda x: x == (-1, -1), self.__wordmapping[0])))
        manunlinked = len(list(filter(lambda x: x == (-1, -1), self.__wordmapping[1])))
        pretty_print += f"\n\n*** {ocrunlinked} unlinked words in OCR/HTR output ({(ocrunlinked / len(self.__wordmapping[0])) * 100:.1f})%, " + \
                        f"{manunlinked} unlinked words in manual transcription ({(manunlinked / len(self.__wordmapping[1])) * 100:.1f})%, " + \
                        f"{self.__manorphannum} ({(self.__manorphannum / manunlinked) * 100:.1f})% of those are orphan words"

        return pretty_print

    @property
    def manfilename(self) -> str:
        return self.__manfilename

    @property
    def ocrfilename(self) -> str:
        return self.__ocrfilename

    @property
    def ngramlen(self) -> int:
        return self.__ngramlen

    @property
    def maxdistprop(self) -> int:
        return self.__maxdistprop

    @property
    def maxdistword(self) -> int:
        return self.__maxdistword

    @property
    def minwordsim(self) -> int:
        return self.__minwordsim

    @property
    def minwordsimstrong(self) -> float:
        return self.__minwordsimstrong

    @property
    def maxngrammulti(self) -> int:
        return self.__maxngrammulti

    @property
    def maxdistunlinked(self) -> int:
        return self.__maxdistunlinked

    @property
    def xmllogchanges(self) -> int:
        return self.__xmllogchanges

    @property
    def logfile(self) -> str:
        return self.__logfile

    @property
    def manlines(self) -> list[str]:
        return self.__manlines

    @property
    def manwords(self) -> list[str]:
        return self.__manwords

    @property
    def manlineswords(self) -> list[list[str]]:
        return self.__manlineswords

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
    def correctedlines(self) -> list[str]:
        return self.__correctedlines

    @property
    def wordmapping(self) -> list[list[tuple[int, int]]]:
        return self.__wordmapping

    def __repr__(self):
        return f"OCRCorrectorManual(ocrfilename=%r, manfilename=%r, ngramlen=%r, maxdistprop=%r, maxdistword=%r, minwordsim=%r, minwordsimstrong=%r, maxngrammulti=%r, " + \
            f"maxdistunlinked=%r, xmllogchanges=%r, logfile=%r, log=%r)" % \
            (self.__ocrfilename, self.__manfilename, self.__ngramlen, self.__maxdistprop, self.__maxdistword,
             self.__minwordsim,
             self.__minwordsimstrong, self.__maxngrammulti, self.__maxdistunlinked, self.__xmllogchanges,
             self.__logfile, self.__log)

    def __str__(self):
        return f"OCR corrector running on PageXML file {self.__ocrfilename} and manual transcription in {self.__manfilename}\n" + \
            f"comparison is based on ngram length {self.__ngramlen}, maximal distance proportion {self.__maxdistprop}, maximal distance between words {self.__maxdistword}\n" + \
            f"minimal Levenshtein ratio between words at same position in matching ngrams {self.__minwordsim}, " + \
            f"strong minimal Levenshtein ratio {self.__minwordsimstrong} between words in ngrams with shorter length than {self.__ngramlen}, " + \
            f"maximal length of {self.__maxngrammulti} for word sequence that can correspond to a single word), " + \
            f"after ngram matching, a maximal distance of {self.__maxdistunlinked} for additional matching words/sequences from linked position, or maximal distance between " + \
            f"linked positions for non-matching words to be linked, " + \
            f"PageXML " + ("does not indicate changes" if self.__xmllogchanges == 0 else \
                               ("indicates changes using special characters" + (
                                   " and by showing original words" if self.__xmllogchanges == 2 else ""))) + \
            f"logging set to {self.__log}\n\n" + \
            self.__get_texts_mappings_pretty_print(maxcount=100)


def process_args_switches():
    """ correction_manual.py --ngramlen [number of words in ngrams that are used for comparison of OCR/HTR output and manual transcription]
                             --maxdistprop [given edit distance between OCR/HTR ngram and transcription ngram, distance divided by length of the latter ngram should not exceed this value]
                             --maxdistword [edit distance should not exceed the value specified x number of words in ngram]
                             --minwordsim (minimal Levenshtein ratio between an OCR/HTR word and a word in manual transcription that have same position in matching ngram)
                             --minwordsimstrong (minimal such ratio between words in ngrams with shorter length than ngram)
                             --maxngrammulti (maximal length of word sequence that can correspond to a single word)
                             --maxdistunlinked (after ngram matching, the maximal distance of additional matching words/sequences from linked position, or maximal distance between
                                                linked positions for non-matching words to be linked)
                             --xlmllogchanges [value determines extent of information on changes logged in PageXML output: 0 = nothing, 1 = special flags for types, 2 = also OCR/HTR words ]
                             --logfile [listing of words in OCR/HTR output, in manual transcription, in corrected version]
                             [OCR output file] [manual transcription] [PageXML output with corrected version]
    """
    switches = {"ngramlen": 3, "maxdistprop": 0.5, "maxdistword": 5, "minwordsim": 0.4, "minwordsimstrong": 0.7,
                "maxngrammulti": 3, "maxdistunlinked": 3, "xmllogchanges": 0, "logfile": ""}
    if len(sys.argv) < 4 or len(sys.argv) % 2 != 0 or (len(sys.argv) >= 6 and sys.argv[1][0:2] != "--"):
        print("syntax of command call not correct")
        return
    ocroutfile, mantrans, outfile = sys.argv[-3:]
    for i in range(1, len(sys.argv) - 3, 2):
        if type(switches[sys.argv[i][2:]]) == int:
            switches[sys.argv[i][2:]] = int(sys.argv[i + 1])
        elif type(switches[sys.argv[i][2:]]) == float:
            switches[sys.argv[i][2:]] = float(sys.argv[i + 1])
        else:
            switches[sys.argv[i][2:]] = sys.argv[i + 1]
    OCRCorrectorManual(ocroutfile, mantrans, **switches).run(outfile)


if __name__ == "__main__":
    process_args_switches()
