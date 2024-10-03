import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from typing import List
import re
import string
from symspellpy import SymSpell, Verbosity


class OCRCorrectorAlt:
    def __init__(self, ocr_content: bytes, mantrans_content: bytes, log: bool = False) -> None:
        self.__ocr_content: bytes = ocr_content
        self.__mantrans_content: bytes = mantrans_content
        self.__log: bool = log
        self.__corrected_content: bytes = b''

    def run(self, add_orig: bool = False, similarity_threshold: float = 0.5) -> None:
        """Executes the OCR correction process."""
        # Extract words from manual transcription
        mantrans_text = self.__mantrans_content.decode('utf-8')
        mantrans_words = self.__tokenize(mantrans_text)

        if self.__log:
            print("Manual Transcription Words:", mantrans_words)

        # Initialize SymSpell
        sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
        for word in mantrans_words:
            sym_spell.create_dictionary_entry(word, 1)

        # Parse OCR content and extract words
        pagexml_output = PageXMLOutputAlt(self.__ocr_content)
        ocr_lines = pagexml_output.read_lines()
        corrected_lines = []

        for line in ocr_lines:
            ocr_words = self.__tokenize(line)
            if self.__log:
                print(f"OCR Line Words: {ocr_words}")

            # Calculate similarity ratio
            s = SequenceMatcher(None, ocr_words, mantrans_words)
            similarity = s.ratio()
            if self.__log:
                print(f"Similarity ratio for line '{line}': {similarity}")

            if similarity < similarity_threshold:
                # Similarity too low; skip correction
                if self.__log:
                    print("Similarity below threshold; leaving line unchanged.")
                corrected_line = line  # Keep the original OCR line
            else:
                if self.__log:
                    print("Similarity above threshold; processing line.")
                corrected_words = self.__align_and_correct(ocr_words, mantrans_words, sym_spell, add_orig)
                corrected_line = self.__reconstruct_line(corrected_words)

            if self.__log:
                print(f"Corrected Line: {corrected_line}")

            corrected_lines.append(corrected_line)

        # Ensure all lines are processed
        if self.__log:
            print("All Corrected Lines:", corrected_lines)

        # Update the PageXML content with corrected lines
        self.__update_pagexml_content(corrected_lines)

    def __tokenize(self, text: str) -> List[str]:
        """Splits text into words, including special characters within words."""
        pattern = r'[^\s\W]+(?:[\'@&][^\s\W]+)*|[^\w\s]'
        tokens = re.findall(pattern, text, re.UNICODE)
        return tokens

    def __align_and_correct(self, ocr_words: List[str], mantrans_words: List[str],
                            sym_spell: SymSpell, add_orig: bool) -> List[str]:
        """Aligns OCR words with manual transcription words and applies corrections."""
        s = SequenceMatcher(None, ocr_words, mantrans_words)
        corrected_words = []
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            if self.__log:
                print(f'{tag} ocr[{i1}:{i2}] man[{j1}:{j2}]')
                print(f'  OCR words: {ocr_words[i1:i2]}')
                print(f'  Manual words: {mantrans_words[j1:j2]}')
            if tag == 'equal':
                corrected_words.extend(ocr_words[i1:i2])
            elif tag == 'replace':
                if (i2 - i1) == (j2 - j1):
                    # Word-level replacement
                    for ocr_word, man_word in zip(ocr_words[i1:i2], mantrans_words[j1:j2]):
                        suggestions = sym_spell.lookup(ocr_word, Verbosity.TOP, max_edit_distance=2)
                        if suggestions and suggestions[0].term == man_word:
                            corrected_word = f'~{man_word}'
                            corrected_words.append(corrected_word)
                        else:
                            corrected_word = f'[{ocr_word}] ~{man_word}'
                            corrected_words.append(corrected_word)
                else:
                    for ocr_word in ocr_words[i1:i2]:
                        corrected_words.append(f'[{ocr_word}]')
                    inserted_words = ' '.join(mantrans_words[j1:j2])
                    corrected_words.append(f'[[{inserted_words}]]')
            elif tag == 'delete':
                for ocr_word in ocr_words[i1:i2]:
                    corrected_words.append(f'[{ocr_word}]')
            elif tag == 'insert':
                inserted_words = ' '.join(mantrans_words[j1:j2])
                corrected_words.append(f'[[{inserted_words}]]')
        return corrected_words

    def __reconstruct_line(self, tokens: List[str]) -> str:
        """Reconstructs the line from tokens, avoiding spaces before punctuation."""
        line = ''
        for i, token in enumerate(tokens):
            if token in string.punctuation:
                prev_token = tokens[i - 1] if i > 0 else ''
                if prev_token.endswith(']]') or prev_token.endswith(']'):
                    line += ' ' + token
                else:
                    line = line.rstrip() + token
            else:
                if line:
                    line += ' ' + token
                else:
                    line += token
        return line

    def __update_pagexml_content(self, corrected_lines: List[str]) -> None:
        """Updates the PageXML content with corrected lines."""
        try:
            tree = ET.ElementTree(ET.fromstring(self.__ocr_content))
            root = tree.getroot()
            namespaces = PageXMLOutputAlt.NAMESPACE
            text_lines = root.findall('.//pc:TextLine', namespaces)
            for line_elem, corrected_line in zip(text_lines, corrected_lines):
                unicode_elem = line_elem.find('.//pc:Unicode', namespaces)
                if unicode_elem is not None:
                    unicode_elem.text = corrected_line
            self.__corrected_content = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        except Exception as e:
            raise Exception("Error updating PageXML content") from e

    @property
    def corrected_content(self) -> bytes:
        return self.__corrected_content

    def __repr__(self) -> str:
        return f"OCRCorrector(log={self.__log})"

    def __str__(self) -> str:
        return f"OCRCorrector"


class PageXMLOutputAlt:
    """
    PageXML file with text areas, lines in text area, and coordinates of areas and lines.
    """
    NAMESPACE = {'pc': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15'}

    def __init__(self, content: bytes = None, log: bool = False) -> None:
        self.__content: bytes = content
        self.__lines: List[str] = []
        self.__log: bool = log

    def read_lines(self) -> List[str]:
        """Parses the PageXML content and extracts text lines."""
        self.__lines = []
        if self.__content is None:
            raise ValueError("No content to read")
        try:
            root = ET.fromstring(self.__content)
            for text_line in root.findall('.//pc:TextLine', self.NAMESPACE):
                text_equiv = text_line.find('.//pc:TextEquiv/pc:Unicode', self.NAMESPACE)
                if text_equiv is not None and text_equiv.text:
                    self.__lines.append(text_equiv.text)
                    if self.__log:
                        print(f"Found TextLine: {text_equiv.text}")
            if self.__log:
                print(f"Total TextLines found: {len(self.__lines)}")
        except Exception as e:
            raise Exception("Error parsing PageXML content") from e
        return self.__lines

    @property
    def content(self) -> bytes:
        return self.__content

    @property
    def lines(self) -> List[str]:
        return self.__lines

    def __repr__(self) -> str:
        return f"PageXMLOutput(log={self.__log})"

    def __str__(self) -> str:
        return f"PageXML output; logging is set to {self.__log}"