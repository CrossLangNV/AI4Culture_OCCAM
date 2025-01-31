import os

from cassis import Cas
from cassis.typesystem import Type, TypeSystem
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.api.options import OptionsAll
from app.schemas.schema import (
    PipelineOptionsResponse,
    ProcessOptions,
    ProcessPipelineResponse,
    TextOptionsBase,
)
from okapi_segmentation.main import okapi_segmentation
from text_parser.sentence_extraction import extract_sentences_from_lines

router = APIRouter()

MIME_TEXT = "text/plain"


class ProcessCas(Cas):
    LINE = "cassis.Line"

    def __init__(self, *args, **kwargs):
        # Typesystem
        typesystem = TypeSystem()
        typesystem.create_type(self.LINE, supertypeName="uima.tcas.Annotation")

        super().__init__(typesystem=typesystem)

    def get_LineType(self) -> Type:
        return self.typesystem.get_type(self.LINE)

    @classmethod
    def from_text(cls, text: list[str]):
        """
        Initialize the CAS
        add the text lines to the CAS
        """

        # Initialize the CAS
        cas = cls()

        # Add the text lines to the CAS
        cas.add_text(text)

        return cas

    def get_original_text(self) -> list[str]:
        """
        Return the original text
        """

        # View 1: The original text
        # Return all lines from the view
        view = self.get_view("_InitialView")
        l = []
        for line in view.select(self.LINE):
            l.append(line.get_covered_text())

        return l

    def add_text(self, text: list[str], name: str = None):
        """
        Add the processed text to the CAS
        :param text: list of text lines
        :param name: name of the view
        :return:
        """
        if name is None:
            view = self
        else:
            view = self.create_view(name)

        text_all = ""
        LineType = self.get_LineType()
        for line_text in text:
            n = len(line_text)
            line = LineType(begin=len(text_all), end=len(text_all) + n)
            text_all += line_text + "\n"
            view.add(line)
        view.sofa_string = text_all
        view.sofa_mime = MIME_TEXT

    def print(self):
        """
        Print the CAS as pretty XMI
        """
        print(self.to_xmi(pretty_print=True))


@router.get(
    "/tools",
    response_model=PipelineOptionsResponse,
    name="pipeline:options",
)
async def get_process_options() -> PipelineOptionsResponse:
    """
    Get Options for Text Segmentation Pipeline

    Returns the available options for the text segmentation pipeline.

    - `options`: List of processing options.
    - `description`: All methods process a list of texts and return a list of processed texts.
    """

    return PipelineOptionsResponse(
        options=OptionsAll().get_options(),
        description="Available options to use in the text segmentation pipeline.",
    )


@router.post("", response_model=ProcessPipelineResponse, name="pipeline:process")
async def post_process(
    data: ProcessOptions,
) -> ProcessPipelineResponse:
    """
    Apply multiple processing methods to a text

    Returns the processed text.
    """

    if not data.options:
        # If no options are selected, return the original text
        return ProcessPipelineResponse(lines=data.lines, language=data.language)

    options = OptionsAll()

    # Ensure that the selected options are valid
    for option in data.options:
        try:
            options.get_option(option)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid option: {option}")

    cas = ProcessCas.from_text(data.lines)

    # Get the original text
    l = cas.get_original_text()

    # Apply the selected options in the specified order
    processed_text = l
    for option in data.options:
        processing_function = options.get_option(option)
        processed_text = processing_function(processed_text)

        cas.add_text(processed_text, option)

    # Return the processed text
    return ProcessPipelineResponse(
        lines=processed_text,
        language=data.language,
        options=data.options,
        cas=cas.to_xmi(),
    )
