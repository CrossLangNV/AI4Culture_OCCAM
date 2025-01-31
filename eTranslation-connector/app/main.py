import asyncio
import base64
import io
import logging
import os
from functools import lru_cache
from time import sleep
from typing import Optional

import databases
import nltk
import requests
import sqlalchemy
from fastapi import (
    FastAPI,
    Form,
    HTTPException,
    File,
    UploadFile,
    Query,
    Request,
    Depends,
)
from fastapi.responses import StreamingResponse
from nltk.tokenize import sent_tokenize
from requests.auth import HTTPDigestAuth
from sqlalchemy import text
from tika import parser as tika_parser

from app import config
from app.models import (
    ETranslationTextRequest,
    ETranslationCallerInformation,
    ETranslationDocumentRequest,
    ETranslationDestinations,
    SupportedFileFormat,
    ETranslationDocumentToTranslateBase64,
)

# SQLAlchemy
DATABASE_URL = "sqlite:///./sqlite.db"

database = databases.Database(DATABASE_URL)

metadata = sqlalchemy.MetaData()

translated_documents = sqlalchemy.Table(
    "translated_documents",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("mime_type", sqlalchemy.String),
    sqlalchemy.Column("source", sqlalchemy.String),
    sqlalchemy.Column("target", sqlalchemy.String),
    sqlalchemy.Column("content", sqlalchemy.String),
    sqlalchemy.Column("completed", sqlalchemy.Boolean),
    sqlalchemy.Column("total_segments", sqlalchemy.Integer),
)

translated_snippets = sqlalchemy.Table(
    "translated_snippets",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("source", sqlalchemy.String),
    sqlalchemy.Column("target", sqlalchemy.String),
    sqlalchemy.Column("content", sqlalchemy.String),
    sqlalchemy.Column("completed", sqlalchemy.Boolean),
    sqlalchemy.Column("total_segments", sqlalchemy.Integer),
)

engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
metadata.create_all(engine)

# FastAPI
tags_metadata = [{"name": "info"}, {"name": "snippets"}, {"name": "documents"}]
app = FastAPI(
    title="CEFAT4CITIES - eTranslation connector",
    description="Translate text snippets and documents with eTranslation.",
    openapi_tags=tags_metadata,
)

logger = logging.getLogger("uvicorn.access")


@lru_cache()
def get_settings():
    return config.Settings()


PATH_DOCUMENT_TRANSLATION = "/hook/document"
PATH_SNIPPET_TRANSLATION = "/hook/snippet"


def get_snippet_callback_url(settings: config.Settings):
    if settings.snippet_callback_url:
        return settings.snippet_callback_url

    assert (
        settings.callback_url
    ), "Either callback_url or snippet_callback_url must be set"

    return settings.callback_url + PATH_SNIPPET_TRANSLATION


def get_document_callback_url(settings: config.Settings):
    if settings.document_callback_url:
        return settings.document_callback_url

    assert (
        settings.callback_url
    ), "Either callback_url or document_callback_url must be set"

    return settings.callback_url + PATH_DOCUMENT_TRANSLATION


@app.on_event("startup")
async def startup():
    logger = logging.getLogger("uvicorn.access")
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    nltk.download("punkt")
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


translation_url = "https://webgate.ec.europa.eu/etranslation/si/translate"

insert_lock = asyncio.Lock()


async def execute_query(query):
    async with insert_lock:  # Prevent concurrent insertions for the same request-id
        await database.execute(query)


async def call_etranslation_snippet(source, target, snippet, settings):
    tika_parsed_content = tika_parser.from_buffer(snippet, "http://tika:9998/tika")

    requester_callback = get_snippet_callback_url(settings)

    snippet = ETranslationTextRequest(
        caller_information=ETranslationCallerInformation(
            application=settings.etranslation_username,
            username=settings.etranslation_username,
        ),
        source_language=source,
        target_languages=[target],
        requester_callback=requester_callback,
        text_to_translate=snippet,
    )
    headers = {"Content-Type": "application/json"}
    logger.info(snippet.json(by_alias=True))
    response = requests.post(
        translation_url,
        data=snippet.json(by_alias=True),
        headers=headers,
        auth=HTTPDigestAuth(
            settings.etranslation_username, settings.etranslation_password
        ),
    )
    response.raise_for_status()
    request_id = response.content.decode()
    total_segments = len(sent_tokenize(tika_parsed_content["content"]))
    # Insert or replace logic
    query = f"""
            INSERT OR REPLACE INTO translated_snippets (id, source, target, completed, total_segments)
            VALUES ('{request_id}', '{source}', '{target}', 0, {total_segments})
        """
    await execute_query(query)
    return request_id


async def call_etranslation_document(
        source, target, supported_format, content, total_segments, settings
):
    generated_file_name = "document." + supported_format.name
    document = ETranslationDocumentRequest(
        caller_information=ETranslationCallerInformation(
            application=settings.etranslation_username,
            username=settings.etranslation_username,
        ),
        source_language=source,
        target_languages=[target],
        destinations=ETranslationDestinations(
            http_destinations=[get_document_callback_url(settings)]
        ),
        document_to_translate_base64=ETranslationDocumentToTranslateBase64(
            format=supported_format.name, content=content, file_name=generated_file_name
        ),
    )
    headers = {"Content-Type": "application/json"}
    logger.info(
        f"Preparing eTranslation document request: Source={source}, Target={target}, Format={supported_format.name}")
    # logger.info(document.json(by_alias=True))
    try:
        response = requests.post(
            translation_url,
            data=document.json(by_alias=True),
            headers=headers,
            auth=HTTPDigestAuth(
                settings.etranslation_username, settings.etranslation_password
            ),
        )
        response.raise_for_status()
        request_id = response.content.decode()
        # if request id is negative, it means that the request was not accepted
        if int(request_id) < 0:
            # log the request
            logger.error(f"eTranslation request not accepted: {request_id}")
            logger.error(f"Request: {document.json(by_alias=True)}")
            raise HTTPException(status_code=400, detail="eTranslation request not accepted")
        logger.info(f"Received request ID: {request_id}")
        # translated_documents[request_id] = {'mime_type': supported_format.value}
        query = f"""
                INSERT OR REPLACE INTO translated_documents (id, mime_type, source, target, completed, total_segments)
                VALUES ('{request_id}', '{supported_format.value}', '{source}', '{target}', 0, {total_segments})
            """
        await execute_query(query)
        logger.info(f"Inserted request {request_id} into the database.")

    # mock translation response to callback
    # mock_document_translation(request_id, target, content, settings)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error in eTranslation API request: {e}")
        raise

    return request_id


def mock_document_translation(request_id, target, content, settings):
    sleep(5)
    parameters = {"request-id": request_id, "target-language": target}
    logger.info(request_id, target, content)
    response = requests.post(
        get_document_callback_url(settings), data=content, params=parameters
    )
    return response


@app.get("/info", tags=["info"])
async def info(settings: config.Settings = Depends(get_settings)):
    return {
        "etranslation_username": settings.etranslation_username,
        "etranslation_password": "***",
        # "snippet_callback_url": get_snippet_callback_url(settings),
        # "document_callback_url": get_document_callback_url(settings),
    }


@app.get("/stats", tags=["stats"])
async def stats():
    count_result_documents = engine.execute(
        text(
            "SELECT source, target, COUNT(*) AS total, SUM(total_segments) AS total_segments "
            "FROM translated_documents "
            "WHERE completed "
            "GROUP BY source, target"
        )
    )

    count_result_snippets = engine.execute(
        text(
            "SELECT source, target, COUNT(*) AS total, SUM(total_segments) AS total_segments "
            "FROM translated_snippets "
            "WHERE completed "
            "GROUP BY source, target"
        )
    )

    return {
        "tanslated_documents": [row for row in count_result_documents],
        "translated_snippets": [row for row in count_result_snippets],
    }


@app.post("/translate/snippet", tags=["snippets"])
async def translate_snippet(
        source: str = Form(...),
        target: str = Form(...),
        snippet: str = Form(...),
        settings: config.Settings = Depends(get_settings),
):
    request_id = await call_etranslation_snippet(source, target, snippet, settings)
    return request_id


@app.get("/translate/snippet/{request_id}", tags=["snippets"])
async def get_translated_snippet(request_id: str):
    query = translated_snippets.select().where(translated_snippets.c.id == request_id)
    translated_snippet = await database.fetch_one(query)
    if translated_snippet["completed"]:
        logger.info(translated_snippet)
        return translated_snippet
    raise HTTPException(status_code=404, detail="Translation not found")


@app.post("/translate/snippet/blocking", tags=["snippets"])
async def translate_snippet_blocking(
        source: str = Form(...),
        target: str = Form(...),
        snippet: str = Form(...),
        settings: config.Settings = Depends(get_settings),
):
    request_id = await call_etranslation_snippet(source, target, snippet, settings)
    query = translated_snippets.select().where(translated_snippets.c.id == request_id)
    translated_snippet = await database.fetch_one(query)
    retries = 0

    while retries < settings.snippet_timeout:
        if translated_snippet is None:
            logger.info("Translation snippet is not yet ready, retrying...")
            await asyncio.sleep(1)
            translated_snippet = await database.fetch_one(query)
            retries += 1
            continue

        if translated_snippet["completed"]:
            break
        await asyncio.sleep(1)
        retries += 1
        translated_snippet = await database.fetch_one(query)

    if translated_snippet and translated_snippet["completed"]:
        return translated_snippet["content"]

    raise HTTPException(status_code=408, detail="Translation timed out")


@app.post("/translate/document", tags=["documents"])
async def translate_document(
        source: str = Form(...),
        target: str = Form(...),
        file: UploadFile = File(...),
        settings: config.Settings = Depends(get_settings),
):
    contents = await file.read()
    tika_parsed_content = tika_parser.from_buffer(contents, "http://tika:9998/tika")
    total_segments = len(sent_tokenize(tika_parsed_content["content"]))
    logger.info("Total segments: %d", total_segments)
    b64_content = base64.b64encode(contents)
    filename, file_extension = os.path.splitext(file.filename)
    supported_format = SupportedFileFormat[file_extension[1:]]
    logger.info(
        "Calling etranslation: source %s, target %s, format %s",
        source,
        target,
        supported_format.name,
    )
    request_id = await call_etranslation_document(
        source, target, supported_format, b64_content, total_segments, settings
    )
    return request_id


@app.post("/translate/document/blocking", tags=["documents"])
async def translate_document_blocking(
        source: str = Form(...),
        target: str = Form(...),
        file: UploadFile = File(...),
        settings: config.Settings = Depends(get_settings),
):
    contents = file.file.read()
    tika_parsed_content = tika_parser.from_buffer(contents, "http://tika:9998/tika")
    total_segments = len(sent_tokenize(tika_parsed_content["content"]))
    logger.info("Total segments: %d", total_segments)
    b64_content = base64.b64encode(contents)
    filename, file_extension = os.path.splitext(file.filename)
    supported_format = SupportedFileFormat[file_extension[1:]]
    logger.info(
        "Calling etranslation: source %s, target %s, format %s",
        source,
        target,
        supported_format.name,
    )
    request_id = await call_etranslation_document(
        source, target, supported_format, b64_content, total_segments, settings
    )

    query = translated_documents.select().where(translated_documents.c.id == request_id)
    translated_document = await database.fetch_one(query)
    retries = 0

    while retries < settings.document_timeout:
        if translated_document is None:
            logger.info("Document translation is not yet ready, retrying...")
            await asyncio.sleep(1)
            translated_document = await database.fetch_one(query)
            retries += 1
            continue

        if translated_document["completed"]:
            break

        await asyncio.sleep(1)
        retries += 1
        translated_document = await database.fetch_one(query)

    if translated_document and translated_document["completed"]:
        translation = translated_document["content"]
        decoded = base64.b64decode(translation)
        # return content with correct mime type
        response = StreamingResponse(
            io.BytesIO(decoded), media_type=translated_document["mime_type"]
        )
        response.headers["Content-Disposition"] = (
                "attachment; filename=" + filename + "_" + target.upper() + file_extension
        )
        return response

    raise HTTPException(status_code=408, detail="Translation timed out")


@app.get("/translate/document/{request_id}", tags=["documents"])
async def get_translated_document(request_id: str):
    query = translated_documents.select().where(translated_documents.c.id == request_id)
    translated_document = await database.fetch_one(query)
    if translated_document["completed"]:
        translated_document_content = translated_document["content"]
        decoded = base64.b64decode(translated_document_content)
        # return content with correct mime type
        mime_type = translated_document["mime_type"]
        response = StreamingResponse(io.BytesIO(decoded), media_type=mime_type)
        response.headers["Content-Disposition"] = (
                "attachment; filename="
                + request_id
                + "."
                + SupportedFileFormat(mime_type).name
        )
        return response
    raise HTTPException(status_code=404, detail="Translation not found")


@app.post(PATH_SNIPPET_TRANSLATION, include_in_schema=False)
async def translate_snippet_callback(
        request_id: str = Form(..., alias="request-id"),
        target_language: str = Form(..., alias="target-language"),
        translated_text: str = Form(..., alias="translated-text"),
        external_reference: Optional[str] = Form(None, alias="external-reference"),
):
    response = {
        "request-id": request_id,
        "target-language": target_language,
        "translated-text": translated_text,
        "external-reference": external_reference,
    }
    logger.info(response)
    query = (
        translated_snippets.update()
        .where(translated_snippets.c.id == request_id)
        .values(content=translated_text, completed=True)
    )
    last_record_id = await database.execute(query)
    return last_record_id


@app.post(PATH_DOCUMENT_TRANSLATION, include_in_schema=False)
async def translate_document_callback(
        request: Request,
        request_id: str = Query(None, alias="request-id"),
        target_language: str = Query(None, alias="target-language"),
):
    body = b""
    async for chunk in request.stream():
        body += chunk
    content_b64 = body.decode()
    response = {
        "request-id": request_id,
        "target-language": target_language,
        "translated-text": content_b64,
    }
    logger.info(response)
    query = (
        translated_documents.update()
        .where(translated_documents.c.id == request_id)
        .values(content=content_b64, completed=True)
    )
    last_record_id = await database.execute(query)
    return last_record_id
