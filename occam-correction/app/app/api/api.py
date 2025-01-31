import logging
import sys

from fastapi import APIRouter, HTTPException


from app.schemas.schema import TextOptionsBase, TextOptionLLM
from post_ocr_correction.main import (
    correct_text_symspell,
    correct_text_symspell_flair_cli,
    correct_llm,
)
from post_ocr_correction.model_utils import LanguageNotSupportedError

api_router = APIRouter(prefix="/tools", tags=["tools"])

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler(sys.stdout)
log_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)

logger.info("API is starting up")


@api_router.post(
    "/sym_spell",
    response_model=TextOptionsBase,
    name="tools:sym_spell",
)
def post_correct_text_symspell(
    data: TextOptionsBase,
) -> TextOptionsBase:
    """
    Correct (OCR) text using SymSpell.

    Returns the corrected text.
    """
    text = data.text
    language = data.language

    response_text = correct_text_symspell(text, language=language)
    response_data = TextOptionsBase(text=response_text, language=language)

    return response_data


@api_router.post(
    "/sym_spell_flair",
    response_model=TextOptionsBase,
    name="tools:sym_spell_flair",
)
def post_correct_text_symspell_flair(
    data: TextOptionsBase,
) -> TextOptionsBase:
    """
    Correct (OCR) text using SymSpell & flair.
    https://github.com/flairNLP/flair

    Returns the corrected text.
    """

    text = data.text
    language = data.language or "en"

    try:
        response_text = correct_text_symspell_flair_cli(text, language)
    except LanguageNotSupportedError as e:
        raise HTTPException(status_code=400, detail="Language not supported")

    response_data = TextOptionsBase(text=response_text, language=language)

    return response_data


@api_router.post(
    "/llm",
    response_model=TextOptionsBase,
    name="tools:llm",
)
def post_correct_text_llm(
    data: TextOptionLLM,
) -> TextOptionsBase:
    """
    Correct (OCR) text using a Large Language Model.

    Returns the corrected text.
    """
    text = data.text
    language = data.language
    prompt = data.prompt

    logger.info("Correcting text using LLM")
    try:
        response_text = correct_llm(text, language, prompt=prompt)
    except Exception as e:
        logger.exception("Failed to correct text using LLM", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))
    response_data = TextOptionsBase(text=response_text, language=data.language)

    return response_data
