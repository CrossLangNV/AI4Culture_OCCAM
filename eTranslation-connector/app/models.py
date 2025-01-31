from enum import Enum
from typing import Optional, List

from pydantic import BaseModel


def to_camel(string: str) -> str:
    components = string.split('_')
    # We capitalize the first letter of each component except the first one
    # with the 'capitalize' method and join them together.
    return components[0] + ''.join(x.capitalize() for x in components[1:])


class SupportedFileFormat(str, Enum):
    odt = 'application/vnd.oasis.opendocument.text'
    ods = 'application/vnd.oasis.opendocument.spreadsheet'
    odp = 'application/vnd.oasis.opendocument.presentation'
    odg = 'application/vnd.oasis.opendocument.graphics'
    ott = 'application/vnd.oasis.opendocument.text-template	'
    ots = 'application/vnd.oasis.opendocument.spreadsheet-template'
    otp = 'application/vnd.oasis.opendocument.presentation-template'
    otg = 'application/vnd.oasis.opendocument.graphics-template'
    rtf = 'application/rtf'
    doc = 'application/msword'
    docx = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    xls = 'application/vnd.ms-excel'
    xlsx = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ppt = 'application/vnd.ms-powerpoint'
    pptx = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    pdf = 'application/pdf'
    txt = 'text/plain'
    htm = 'text/html'
    html = 'text/html'
    xhtml = 'application/xhtml+xml'
    xml = 'text/xml'
    xlf = 'application/xliff+xml'
    xliff = 'application/xliff+xml'
    sdlxliff = 'application/xliff+xml'
    tmx = 'text/xml'
    rdf = 'application/rdf+xml'


class ETranslationCallerInformation(BaseModel):
    application: str
    username: str


class ETranslationDestinations(BaseModel):
    http_destinations: Optional[List[str]]

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True


class ETranslationBaseRequest(BaseModel):
    caller_information: ETranslationCallerInformation
    source_language: str
    target_languages: List[str]
    domain: Optional[str] = "SPD"
    requester_callback: Optional[str]


class ETranslationTextRequest(ETranslationBaseRequest):
    text_to_translate: str

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True


class ETranslationDocumentToTranslateBase64(BaseModel):
    format: str
    file_name: Optional[str]
    content: str

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True


class ETranslationDocumentRequest(ETranslationBaseRequest):
    destinations: ETranslationDestinations
    document_to_translate_base64: ETranslationDocumentToTranslateBase64
    with_quality_estimate = False

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True


class TranslatedSnippet(BaseModel):
    id: str
    content: str
    completed: bool


class TranslatedDocument(BaseModel):
    id: str
    content: str
    mime_type: str
    completed: bool
