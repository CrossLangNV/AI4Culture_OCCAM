import abc
import copy
import io
import logging
from enum import Enum
from typing import Optional, Type, Union

from lxml import etree
from pydantic import BaseModel

import translation.connector
from correction.connector import CorrectionConnector
from segmentation.connector import (
    SegmentationConnector,
    SegmentationResponse,
)

logger = logging.getLogger(__name__)


class Text(list):
    """
    A class to represent text (from e.g. a PageXML file)

    Contains paragraphs and sentences/textlines

    Example:
    [
        ["This is a sentence.", "This is another sentence."],
        ["This is a new paragraph."]
    ]
    """

    def __init__(self, *args, **kwargs):
        super(Text, self).__init__(*args, **kwargs)

    def __str__(self):
        return "[" + ",\n ".join([str(paragraph) for paragraph in self]) + "]"

    def __repr__(self):
        return self.__str__()


class Paragraph(list):
    """
    A class to represent a paragraph

    Contains sentences/textlines

    Example:
    ["This is a sentence.", "This is another sentence."]
    """

    def __init__(self, *args, **kwargs):
        super(Paragraph, self).__init__(*args, **kwargs)


class PageXMLParser(etree.XMLParser):
    def __init__(self, *args, remove_blank_text=True, **kwargs):
        super(PageXMLParser, self).__init__(
            *args, remove_blank_text=remove_blank_text, **kwargs
        )


class PageXMLWrapper(object):
    """
    Can't inherit from etree._ElementTree directly because it's a C extension
    """

    def __init__(self, *args, parser=None, **kwargs):
        # super(PageXMLTree, self).__init__(*args, **kwargs)

        self._tree = None

        if parser is None:
            parser = PageXMLParser()
        self._parser = parser

    def parse(self, filename):
        self._tree = etree.parse(filename, parser=self._parser)

        # Clean elements, trim text
        for element in self.tree.iter():
            if element.text:
                element.text = element.text.strip()
            if element.tail:
                element.tail = element.tail.strip()

        return self

    @property
    def tree(self) -> etree._ElementTree:
        if self._tree is None:
            raise ValueError("Tree not loaded yet")
        return self._tree

    @property
    def xmlns(self):
        return self.tree.getroot().tag.split("}")[0].strip("{")

    def get_paragraphs(self) -> Text:
        text = Text()
        for region in self.tree.iterfind(".//{%s}TextRegion" % self.xmlns):
            # region

            paragraph = Paragraph()

            for textline in region.iterfind(
                    ".//{{{xmlns}}}TextLine".format(xmlns=self.xmlns)
            ):
                text_textline = self._get_text_from_textline_lxml(textline)
                paragraph.append(text_textline)

            text.append(paragraph)

        return text

    def _get_unique_lxml_child(self, element, path):
        a = list(element.iterfind(path))

        if len(a) != 1:
            raise AssertionError(f"Should only find one {path} element: {a}")

        b = a[0]

        return b

    def _get_text_from_textline_lxml(self, element):
        xmlns = self.xmlns

        path = "{{{xmlns}}}TextEquiv/{{{xmlns}}}Unicode".format(xmlns=xmlns)

        unicode = self._get_unique_lxml_child(element, path)
        unicode_text = unicode.text
        return unicode_text.strip() if unicode_text else ""

    def __str__(self):
        return etree.tostring(self.tree, encoding="utf-8", pretty_print=True).decode(
            "utf-8"
        )

    def write(self, filename, *args, encoding="utf-8", pretty_print=True, **kwargs):
        self.tree.write(
            filename, *args, encoding=encoding, pretty_print=pretty_print, **kwargs
        )


class TextParser(Text):
    @classmethod
    def from_text_lines(cls, lines: list[str]):
        # Clean lines
        lines = list(map(str.strip, lines))

        text = cls()

        # Split on empty lines
        paragraph = Paragraph()
        for line in lines:
            if not line:
                text.append(paragraph)
                paragraph = Paragraph()
            else:
                paragraph.append(line)
        if paragraph:
            text.append(paragraph)

        return text

    @classmethod
    def from_string(cls, s: str):
        text = cls()

        lines = s.splitlines()

        return cls.from_text_lines(lines)

    @classmethod
    def from_file(cls, file):
        """
        Parse a text file

        :param file:
        :return:
        """

        lines = map(lambda b: b.decode("utf-8").strip(), file.readlines())

        return cls.from_text_lines(lines)


class PipelineStep(abc.ABC):
    def __init__(self, *args, **kwargs):
        pass

    def forward(self, x):
        return x

    def backward(self, y):
        return y


class PageXMLParagraphParser(PipelineStep):
    def __init__(self):
        self._page_xml = None

    @property
    def state(self) -> PageXMLWrapper:
        if self._page_xml is None:
            raise ValueError("State not set yet. Run forward first.")

        return self._page_xml

    def set_state(self, x: PageXMLWrapper):
        """
        Intermediate state, required for the backward pass
        :param x:
        :return:
        """
        self._page_xml = x

    def forward(self, x: PageXMLWrapper) -> Text:
        """
        Extract paragraphs from the page xml
        """

        self.set_state(x)

        return x.get_paragraphs()

    def backward(self, y: Text) -> PageXMLWrapper:
        """
        Rebuild the page xml with (new) paragraphs

        :return:
        """

        # Copy the original tree
        page_xml_restored = PageXMLWrapper()
        page_xml_restored._tree = copy.deepcopy(self.state.tree)

        for i_p, (paragraph, text_region) in enumerate(
                zip(
                    y,
                    page_xml_restored.tree.iterfind(
                        ".//{%s}TextRegion" % page_xml_restored.xmlns
                    ),
                )
        ):
            for i_s, (sentence, text_line) in enumerate(
                    zip(
                        paragraph,
                        text_region.iterfind(
                            ".//{{{xmlns}}}TextLine".format(xmlns=page_xml_restored.xmlns)
                        ),
                    )
            ):
                logger.debug(f"Paragraph {i_p} Sentence {i_s}: {sentence}")
                # Update the text
                unicode = page_xml_restored._get_unique_lxml_child(
                    text_line,
                    "{{{xmlns}}}TextEquiv/{{{xmlns}}}Unicode".format(
                        xmlns=page_xml_restored.xmlns
                    ),
                )
                unicode.text = sentence

        return page_xml_restored


class TextParagraphParser(PipelineStep):
    """
    Work with flat text files
    """

    def forward(self, x: str) -> Text:
        """
        Parse the text file into paragraphs

        :return:
        """
        return TextParser.from_string(x)

    def backward(self, y: Text) -> str:
        """
        Convert paragraphs back to text

        :return:
        """

        return (
                "\n\n".join(
                    "\n".join(sentence for sentence in paragraph) for paragraph in y
                )
                + "\n"
        )


class OCRCorrectionStep(PipelineStep, abc.ABC):
    def __init__(self, source_lang):
        super(OCRCorrectionStep, self).__init__()
        self._lang = source_lang
        self._connector = CorrectionConnector()

    @property
    def connector(self):
        return self._connector

    @property
    def lang(self):
        return self._lang

    @abc.abstractmethod
    def correction_method(self, text_flat: str):
        pass

    def correction(self, paragraph: Paragraph) -> Paragraph:
        text_flat = "\n".join(paragraph)
        correction_response = self.correction_method(text_flat)

        return Paragraph(correction_response.text.splitlines(keepends=False))

    def forward(self, x: Text):
        """
        Correct OCR errors

        :return:
        """

        y = Text()
        for paragraph in x:
            paragraph_corrected = self.correction(paragraph)
            y.append(paragraph_corrected)

        return y


class OCRCorrectionSymSpellStep(OCRCorrectionStep):
    def correction_method(self, text_flat: str):
        return self.connector.correct_sym_spell(text_flat, language=self.lang)


class OCRCorrectionSymSpellFlairStep(OCRCorrectionStep):
    def correction_method(self, text_flat: str):
        return self.connector.correct_sym_spell_flair(text_flat, language=self.lang)


class OCRCorrectionLLMStep(OCRCorrectionStep):
    def correction_method(self, text_flat: str):
        return self.connector.correct_llm(text_flat, language=self.lang)


class SegmentationMixin:
    sep = " "
    n_sep = len(sep)

    def __init__(self, *args, **kwargs):
        self._n_x_in = None
        self._n_x_out = None

    @property
    def n_x_in(self):
        if self._n_x_in is None:
            raise ValueError("n_x_in not set yet. Run forward first.")

        return self._n_x_in

    @property
    def n_x_out(self):
        if self._n_x_out is None:
            raise ValueError("n_x_out not set yet. Run forward first.")

        return self._n_x_out

    @staticmethod
    def calc_line_lengths(text: Text):
        """
        Calculate the length of each line in each paragraph

        :return:
        """

        return [[len(line) for line in paragraph] for paragraph in text]

    def n_total(self, n_x: list[int]):
        """
        Total number of characters, if the sentences are concatenated with a space
        """
        return sum(n_x) + self.n_sep * (len(n_x) - 1)

    def calculate_split_indices(self, l_cumsum: list[int], text_joined) -> list[int]:
        """
        Find first empty space
        :param l:
        :return:
        """

        l_indices = [text_joined.find(self.sep, i_start) for i_start in l_cumsum]
        # When str.find finds nothing returns 1 -> Replace -1 with the end of the string
        l_indices = [a if a != -1 else len(text_joined) for a in l_indices]
        return l_indices


class SegmentationStepShared(PipelineStep, SegmentationMixin, abc.ABC):
    def __init__(self, source_lang: str):
        super().__init__()
        super(SegmentationMixin, self).__init__()

        self._lang = source_lang

        self._connector = SegmentationConnector()

    @abc.abstractmethod
    def pipeline_method(self, paragraph: Paragraph) -> SegmentationResponse:
        ...

    def forward(self, x: Text):
        """
        Split paragraphs into sentences

        :return:
        """

        y = Text()

        for paragraph in x:
            paragraph_sentences = self.pipeline_method(paragraph)

            y.append(Paragraph(paragraph_sentences.lines))

        self._n_x_in = self.calc_line_lengths(x)
        self._n_x_out = self.calc_line_lengths(y)

        return y

    def backward(self, y: Text):
        """
        Break sentences back into original paragraphs

        :return:
        """

        text_restored = Text()
        for paragraph, n_x_in_i, n_x_out_i in zip(y, self.n_x_in, self.n_x_out):
            paragraph_joined = self.sep.join(paragraph)

            n_y_in_i = [len(sentence) for sentence in paragraph]

            total_x_out = self.n_total(n_x_out_i)
            if total_x_out == 0:
                logger.warning("n_x_out_i is zero, cannot perform division. Setting fraction to 0.")
                fraction = 0  # Default value or handle as needed
            else:
                fraction = self.n_total(n_y_in_i) / total_x_out

            logger.debug(f"Calculated fraction: {fraction}")

            n_x_in_cumsum = [
                sum(n_x_in_i[: i + 1]) + i * self.n_sep for i in range(len(n_x_in_i))
            ]
            n_y_out_cumsum_ = [
                round(fraction * n_x_in_cumsum_i) for n_x_in_cumsum_i in n_x_in_cumsum
            ]

            n_y_out_cumsum = self.calculate_split_indices(
                n_y_out_cumsum_, paragraph_joined
            )

            paragraph_restored = []
            for i, n_y_out_cumsum_i in enumerate(n_y_out_cumsum):
                i0 = 0 if i == 0 else n_y_out_cumsum[i - 1] + self.n_sep
                i1 = (
                    len(paragraph_joined)
                    if i >= len(n_y_out_cumsum) - 1
                    else n_y_out_cumsum[i]
                )

                sentence = paragraph_joined[i0:i1]

                paragraph_restored.append(sentence)

            text_restored.append(paragraph_restored)

        return text_restored


class DehyphenationStep(SegmentationStepShared):
    def pipeline_method(self, paragraph: Paragraph):
        return self._connector.pipeline(
            paragraph,
            language=self._lang,
            options=[SegmentationConnector.OPTIONS.DEHYPHENATION.value],
        )


class JoinLinesStep(SegmentationStepShared):
    def pipeline_method(self, paragraph: Paragraph):
        return self._connector.pipeline(
            paragraph,
            language=self._lang,
            options=[SegmentationConnector.OPTIONS.JOIN_LINES.value],
        )


class SentenceSegmentationOkapiStep(SegmentationStepShared):
    def pipeline_method(self, paragraph: Paragraph):
        return self._connector.pipeline(
            paragraph,
            language=self._lang,
            options=[SegmentationConnector.OPTIONS.SENTENCE_SEGMENTATION_OKAPI.value],
        )


class SegmentationStep(SegmentationStepShared):
    def pipeline_method(self, paragraph: Paragraph):
        return self._connector.pipeline(
            paragraph, language=self._lang, options=self._connector.options
        )


class JoinAllStep(PipelineStep, SegmentationMixin):
    """
    Joins all the text into one single paragraph with a single sentence
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        super(SegmentationMixin, self).__init__()

        self.sep = " "
        self.n_sep = len(self.sep)

    def forward(self, x: Text):
        """
        Join all the text into one single paragraph with a single sentence

        :return:
        """

        y = Text(
            [[self.sep.join(sentence for paragraph in x for sentence in paragraph)]]
        )

        self._n_x_in = self.calc_line_lengths(x)
        self._n_x_out = self.calc_line_lengths(y)

        return y

    def backward(self, y: Text):
        """
        Break text back into original paragraphs

        :return:
        """

        assert len(y) == 1, "Only one paragraph expected"
        assert len(y[0]) == 1, "Only one sentence expected"

        paragraph_joined = y[0][0]
        n_y_in = len(paragraph_joined)

        assert len(self.n_x_out) == 1, "Only one paragraph expected"
        assert len(self.n_x_out[0]) == 1, "Only one sentence expected"

        n_x_out = self.n_x_out[0][0]

        fraction = n_y_in / n_x_out

        def cumsum(l: list[int]):
            return [sum(l[: i + 1]) + i * self.n_sep for i in range(len(l))]

        n_x_in_cumsum = cumsum(
            [n_i_j for n_x_in_i in self.n_x_in for n_i_j in n_x_in_i]
        )
        n_y_out_cumsum = [
            round(fraction * n_x_in_cumsum_ij) for n_x_in_cumsum_ij in n_x_in_cumsum
        ]

        n_y_out_split_index = self.calculate_split_indices(
            n_y_out_cumsum, paragraph_joined
        )

        text_restored = Text()
        i = 0

        for n_paragraph in self.n_x_in:
            paragraph_restored = Paragraph()
            for _ in n_paragraph:
                i0 = 0 if i == 0 else n_y_out_split_index[i - 1] + self.n_sep
                i1 = n_y_out_split_index[i]

                paragraph_restored.append(paragraph_joined[i0:i1])
                i += 1

            text_restored.append(paragraph_restored)

        return text_restored


class TranslationStep(PipelineStep):
    def __init__(self, source_lang, target_lang):
        self.connector = translation.connector.CEFETranslationConnector()
        self.source_lang = source_lang
        self.target_lang = target_lang

    def forward(self, x: Text):
        """
        Translate the text

        :return:
        """

        x_translated = Text(Paragraph([None] * len(paragraph)) for paragraph in x)

        for i, paragraph in enumerate(x):
            # convert paragraph to file

            with io.BytesIO() as f_paragraph:
                for sentence in paragraph:
                    f_paragraph.write(sentence.encode("utf-8"))
                    f_paragraph.write(b"\n")

                f_paragraph.seek(0)
                paragraph_translated = self.connector.translate_file(
                    ("filename.txt", f_paragraph, "text/plain"),
                    self.source_lang,
                    self.target_lang,
                )

            l_translation = paragraph_translated.decode("utf-8").splitlines(
                keepends=False
            )
            # Cleaning
            l_translation = list(map(str.strip, l_translation))

            assert len(l_translation) == len(
                paragraph
            ), f"Lengths do not match: {len(l_translation)} != {len(paragraph)}"

            for j, sentence_translation in enumerate(l_translation):
                x_translated[i][j] = sentence_translation

        return x_translated

    def backward(self, y: Text):
        """
        Translate the text back

        :return:
        """
        return y


class StepInfo(BaseModel):
    step_class: Optional[Type[PipelineStep]]  # Allow None values
    name: str
    description: Optional[str]


# Enum of steps
class PipelineStepEnum(Enum):
    DEHYPHENATION = StepInfo(
        name="Dehyphenation",
        step_class=DehyphenationStep,
        description="Apply dehyphenation to the text."
    )
    JOIN_PARAGRAPH = StepInfo(
        name="Join Paragraph",
        step_class=JoinLinesStep,
        description="Join all text within each paragraph into a single line."
    )
    SENTENCE_SEGMENTATION = StepInfo(
        name="Sentence Segmentation",
        step_class=SentenceSegmentationOkapiStep,
        description="Split each line into sentences."
    )
    CORRECTION_SYMSPELL = StepInfo(
        name="Correction (SymSpell)",
        step_class=OCRCorrectionSymSpellStep,
        description="Post-OCR correction using SymSpell."
    )
    CORRECTION_SYMSPELL_FLAIR = StepInfo(
        name="Correction (SymSpell+Flair)",
        step_class=OCRCorrectionSymSpellFlairStep,
        description="Post-OCR correction using SymSpell and Flair."
    )
    CORRECTION_LLM = StepInfo(
        name="Correction (LLM)",
        step_class=OCRCorrectionLLMStep,
        description="Post-OCR correction using a Large Language Model (LLM)."
    )
    JOIN_PAGE = StepInfo(
        name="Join Page",
        step_class=JoinAllStep,
        description="Join all text into a single line."
    )
    RENDER_TXT = StepInfo(
        name="Render TXT",
        step_class=None,
        description="Return the result as plain text."
    )

    def get_step(self):
        return self.value.step_class

    @staticmethod
    def get_steps():
        return [step for step in PipelineStepEnum if step.value.step_class is not None]

    @staticmethod
    def get_representation():
        return [
            {
                "key": step.name,
                "name": step.value.name,
                "description": step.value.description,
            }
            for step in PipelineStepEnum
        ]

    @staticmethod
    def get_by_key(key) -> Type[PipelineStep]:
        try:
            step_info = PipelineStepEnum[key.upper()].value
            if step_info.step_class is None:
                raise ValueError(f"No step class defined for {key}")
            return step_info.step_class
        except KeyError:
            raise ValueError(f"Invalid pipeline option key: {key}")


def ocr_pipeline(
        page: Union[PageXMLWrapper, str],
        source_lang: str,
        steps: list[PipelineStep] = None,
        reconstruct: bool = None,  # Default is True
) -> PageXMLWrapper:
    """
       Apply extra steps to the OCR pipeline:

       pipeline:
       - Step 1: Parse the text/page xml
           - Extract paragraphs
       - Step 2.1: Post-OCR correction (TODO)
       - Step 2.2: Convert paragraphs to sentences (TODO)
           - Split paragraphs into sentences
       - Step 4: Restore to PageXML

    :return:
    """

    if reconstruct is None:
        """
        By default, reconstruct the page xml
        """
        reconstruct = True

    if steps is None:
        """
        By default, only segmentation is applied
        """
        steps = [
            PipelineStepEnum.DEHYPHENATION.get_step(),
            PipelineStepEnum.JOIN_PARAGRAPH.get_step(),
            PipelineStepEnum.SENTENCE_SEGMENTATION.get_step()
        ]

    pipe = []
    if isinstance(page, PageXMLWrapper):
        pipe.append(PageXMLParagraphParser())
    else:
        pipe.append(TextParagraphParser())

    for step in steps:
        pipe.append(step(source_lang=source_lang))

    x = page

    for step in pipe:
        x = step.forward(x)

    if not reconstruct:
        return x

    for step in reversed(pipe):
        x = step.backward(x)

    return x


def translate_pipeline(
        page: Union[PageXMLWrapper, str],
        source_lang: str,
        target_lang: str,
        steps: list[PipelineStep] = None,
        reconstruct: bool = None,  # Default is True
) -> PageXMLWrapper:
    """
    Translate the page xml

    pipeline:
    - Step 1: Parse the text/page xml
        - Extract paragraphs
    - Step 2.1: Post-OCR correction (TODO)
    - Step 2.2: Convert paragraphs to sentences (TODO)
        - Split paragraphs into sentences
    - Step 3: Translate sentences
    - Step 4: Convert sentences to back to paragraphs

    :return:
    """

    if reconstruct is None:
        """
        By default, reconstruct the page xml
        """
        reconstruct = True

    if steps is None:
        """
        By default, segmentation and correction are applied
        """
        steps = [
            PipelineStepEnum.DEHYPHENATION.get_step(),
            PipelineStepEnum.JOIN_PARAGRAPH.get_step(),
            PipelineStepEnum.SENTENCE_SEGMENTATION.get_step(),
            PipelineStepEnum.CORRECTION_SYMSPELL_FLAIR.get_step(),
        ]

    pipe = []
    if isinstance(page, PageXMLWrapper):
        pipe.append(PageXMLParagraphParser())
    else:
        pipe.append(TextParagraphParser())

    for step in steps:
        pipe.append(step(source_lang=source_lang))

    pipe.append(TranslationStep(source_lang=source_lang, target_lang=target_lang))

    x = page

    for step in pipe:
        x = step.forward(x)

    if not reconstruct:
        return x

    for step in reversed(pipe):
        x = step.backward(x)

    return x
