"""
Connector methods to POST-OCR correction API.
"""

import os
import time
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
    LLM_JSON_PARSE_RETRIES = int(os.environ.get("CORRECTION_LLM_RETRIES", "3"))
    LLM_RETRY_DELAY_SECONDS = float(os.environ.get("CORRECTION_LLM_RETRY_DELAY", "1.0"))

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
        last_response = None

        for attempt in range(1, self.LLM_JSON_PARSE_RETRIES + 1):
            response = requests.post(
                url,
                json=data,
                timeout=120,
            )
            last_response = response

            if response.ok:
                return CorrectionResponse(**response.json())

            response_text = response.text or ""
            is_retryable_parse_failure = (
                response.status_code >= 500
                and "Could not parse as JSON" in response_text
                and attempt < self.LLM_JSON_PARSE_RETRIES
            )
            if is_retryable_parse_failure:
                time.sleep(self.LLM_RETRY_DELAY_SECONDS)
                continue

            raise_response(response)

        raise_response(last_response)
