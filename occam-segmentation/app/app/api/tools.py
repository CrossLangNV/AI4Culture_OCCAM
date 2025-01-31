import os

from cassis import Cas
from cassis.typesystem import Type, TypeSystem
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.api.options import OptionsAll
from app.schemas.schema import (
    ProcessOptions,
    ProcessPipelineResponse,
    ProcessResponse,
    TextOptionsBase,
)
from okapi_segmentation.main import okapi_segmentation
from text_parser.sentence_extraction import extract_sentences_from_lines

router = APIRouter()


MIME_TEXT = "text/plain"


@router.post(
    "/sentence_from_lines",
    response_model=ProcessResponse,
    name="tools:sentences_from_lines",
)
def post_extract_sentences_from_lines(
    data: TextOptionsBase,
) -> ProcessResponse:
    """
    Extract individual sentences from a list of text lines,
    employing line concatenation and sentence segmentation.

    Returns the extracted sentences as a list of strings.
    """

    text_segmented = extract_sentences_from_lines(data.lines, data.language)

    return ProcessResponse(lines=text_segmented, language=data.language)


@router.post(
    "/sentence_from_lines/file",
    response_class=StreamingResponse,
    name="tools:sentences_from_lines:file",
)
async def post_extract_sentences_from_lines_file(
    file: UploadFile = File(..., media_type=MIME_TEXT),
    language: str = Form("en"),
) -> StreamingResponse:
    """
    Extract individual sentences from a file of text lines (one line per sentence),
    employing line concatenation and sentence segmentation.

    Returns the extracted sentences as text file with one sentence per line.
    """

    text = await file.read()

    sentences = extract_sentences_from_lines(text.decode().splitlines(), language)

    def generate_sentences():
        for sentence in sentences:
            yield sentence + "\n"

    basename, ext = os.path.splitext(file.filename)

    filename = f"{basename}_sentences{ext}"

    return StreamingResponse(
        generate_sentences(),
        media_type=MIME_TEXT,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post(
    "/okapi_segmentation",
    response_model=ProcessResponse,
    name="tools:okapi_segmentation",
)
def post_extract_sentences_from_lines_okapi(
    data: TextOptionsBase,
) -> ProcessResponse:
    """

    Extract individual sentences from a list of text lines,
    employing Okapi line concatenation and sentence segmentation.

    Returns the extracted sentences as a list of strings.
    """

    text_segmented = okapi_segmentation(data.lines, data.language)

    return ProcessResponse(lines=text_segmented)
