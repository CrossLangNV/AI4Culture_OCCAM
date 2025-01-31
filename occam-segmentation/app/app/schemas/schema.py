from typing import Optional

from pydantic import BaseModel, Field

from app.api.options import Dehypenation, JoinTextLines, SentenceSegmentationOkapi


language_field = Field(description="Language code of the text")
options_field = Field(description="List of processing option names")


class TextOptionsBase(BaseModel):
    lines: list[str]
    language: Optional[str] = language_field

    class Config:
        schema_extra = {
            "example": {
                "lines": [
                    "This is a sent-",
                    "ence. This is",
                    "another sentence.",
                    "As you can see, it",
                    "is split over multi-",
                    "ple lines.",
                ],
                "language": "en",
            },
        }


class ProcessOptions(TextOptionsBase):
    options: Optional[list[str]] = options_field

    class Config:
        schema_extra = {
            "example": {
                "lines": [
                    "This is a sent-",
                    "ence. This is",
                    "another sentence.",
                    "As you can see, it",
                    "is split over multi-",
                    "ple lines.",
                ],
                "language": "en",
                "options": [
                    "dehyphenation",
                    "join_lines",
                    "sentence_segmentation/okapi",
                ],
            },
        }


class PipelineOption(BaseModel):
    name: str
    description: str

    class Config:
        schema_extra = {
            "example": {
                "name": "dehyphenation",
                "description": "Re-join hyphenated words",
            },
        }


class PipelineOptionsResponse(BaseModel):
    options: list[PipelineOption]
    description: str

    class Config:
        schema_extra = {
            "example": {
                "options": [
                    PipelineOption(
                        name="dehyphenation", description="Re-join hyphenated words"
                    ).dict(),
                    PipelineOption(
                        name="join_lines",
                        description="Join text lines into one single text",
                    ).dict(),
                ],
                "description": "Available options to use in the text segmentation pipeline.",
            },
        }


class ProcessResponse(BaseModel):
    lines: list[str] = Field(..., description="List of processed text lines")
    language: Optional[str] = language_field

    class Config:
        schema_extra = {
            "example": {
                "lines": [
                    "This is a sentence.",
                    "This is another sentence.",
                    "As you can see, it is split over multiple lines.",
                ],
                "language": "en",
            },
        }


class ProcessPipelineResponse(ProcessResponse):
    options: Optional[list[str]] = options_field
    cas: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "lines": [
                    "This is a sentence.",
                    "This is another sentence.",
                    "As you can see, it is split over multiple lines.",
                ],
                "language": "en",
                "options": [
                    Dehypenation().name,
                    JoinTextLines().name,
                    SentenceSegmentationOkapi().name,
                ],
                "cas": "<?xml version='1.0' encoding='UTF-8'?>\n"
                '<xmi:XMI xmlns:xmi="http://www.omg.org/XMI" xmlns:cas="http:///uima/cas.ecore" xmlns:cassis="http:///cassis.ecore" xmi:version="2.0">\n'
                '   <cas:NULL xmi:id="0"/>\n'
                "</xmi:XMI>\n",
            },
        }
