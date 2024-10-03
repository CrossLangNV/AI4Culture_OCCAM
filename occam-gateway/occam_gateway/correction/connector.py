"""
Connector methods to POST-OCR correction API.
"""

import os
import urllib.parse
from typing import Optional

import requests
from pydantic import BaseModel

from gateway_utils.connector_utils import raise_response


class CorrectionResponse(BaseModel):
    text: str
    language: str
    info: Optional[str]


class CorrectionConnector:
    URL = os.environ.get("CORRECTION_URL", "http://host.docker.internal:18100")

    def health(self) -> bool:
        response = requests.get(self.URL)

        return response.ok

    def correct_sym_spell(self, text: str, language: str) -> CorrectionResponse:
        data = {
            "text": text,
            "language": language,
        }

        url = urllib.parse.urljoin(self.URL, "tools/sym_spell")
        response = requests.post(
            url,
            json=data,
        )

        if not response.ok:
            raise_response(response)

        return CorrectionResponse(**response.json())

    def correct_sym_spell_flair(self, text: str, language: str) -> CorrectionResponse:
        data = {
            "text": text,
            "language": language,
        }

        url = urllib.parse.urljoin(self.URL, "tools/sym_spell_flair")
        response = requests.post(
            url,
            json=data,
        )

        if not response.ok:
            raise_response(response)

        return CorrectionResponse(**response.json())

    def correct_llm(
        self, text: str, language: str, prompt: str = None
    ) -> CorrectionResponse:
        data = {
            "text": text,
            "language": language,
        }

        if prompt:
            data["prompt"] = prompt

        url = urllib.parse.urljoin(self.URL, "tools/llm")
        response = requests.post(
            url,
            json=data,
        )

        if not response.ok:
            raise_response(response)

        return CorrectionResponse(**response.json())
