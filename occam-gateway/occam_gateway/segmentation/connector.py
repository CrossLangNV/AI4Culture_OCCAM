"""
Connector methods to text sentence/line segmentation API.
"""

import os
import urllib.parse
from enum import Enum

import requests
from pydantic import BaseModel
from typing import Optional

from gateway_utils.connector_utils import raise_response


class SegmentationResponse(BaseModel):
    lines: list[str]
    language: Optional[str]
    options: Optional[list[str]]
    cas: Optional[str]


class SegmentationOption(BaseModel):
    name: str
    description: Optional[str]


class SegmentationOptionsResponse(BaseModel):
    options: list[SegmentationOption]
    description: Optional[str]


class SegmentationConnector:
    URL = os.environ.get("SEGMENTATION_URL", "http://host.docker.internal:17100")

    class OPTIONS(Enum):
        DEHYPHENATION = SegmentationOption(
            name="dehyphenation", description="Apply dehyphenation to the text"
        )
        JOIN_LINES = SegmentationOption(
            name="join_lines",
            description="Join all the text within each paragraph into a single line",
        )
        SENTENCE_SEGMENTATION_OKAPI = SegmentationOption(
            name="sentence_segmentation/okapi",
            description="Split each line into sentences if possible",
        )

    def health(self) -> bool:
        response = requests.get(self.URL)

        return response.ok

    @property
    def options(self) -> list[SegmentationOption]:
        return [option.value for option in self.OPTIONS]

    def online_options(self) -> list[SegmentationOption]:
        url = urllib.parse.urljoin(self.URL, "process/pipeline/tools")
        response = requests.get(url)

        if not response.ok:
            raise_response(response)

        return SegmentationOptionsResponse(**response.json()).options

    def assert_options_up_to_date(self):
        online_options = self.online_options()
        online_option_names = [option.name for option in online_options]
        options = self.options

        for option in options:
            if option.name not in online_option_names:
                raise AssertionError("Options are not up to date")

    def pipeline(
        self, text_lines: list[str], language, options: list[SegmentationOption]
    ) -> SegmentationResponse:
        data = {
            "lines": text_lines,
            "language": language,
            "options": [option.name for option in options],
        }

        url = urllib.parse.urljoin(self.URL, "process/pipeline")
        response = requests.post(
            url,
            json=data,
        )

        if not response.ok:
            raise_response(response)

        return SegmentationResponse(**response.json())
