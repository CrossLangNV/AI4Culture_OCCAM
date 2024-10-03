"""
Connector to CEF ETranslation API
"""

import abc
import io
import logging

import os
import urllib.parse
from typing import Union

import requests

from gateway_utils.connector_utils import raise_response

logger = logging.getLogger(__name__)


class TranslationConnector(abc.ABC):
    pass


class CEFETranslationConnector(TranslationConnector):
    URL = os.environ.get("CEF_ETRANSLATION", "http://localhost:28000")

    def health(self) -> bool:
        url = urllib.parse.urljoin(self.URL, "docs")
        response = requests.get(url)
        return response.ok

    def translate_snippet(self, snippet: str, source: str, target: str) -> str:
        """
        Translate a snippet from source to target language.
        :param snippet:
        :param source:
        :param target:
        :return:
        """

        # API fails on empty strings
        if not snippet.strip():
            return snippet

        url = urllib.parse.urljoin(self.URL, "translate/snippet/blocking")

        response_translate_snippet = self.handle_post_request(
            url, data={"source": source, "target": target, "snippet": snippet}
        )

        return response_translate_snippet.json()

    def translate_file(
        self, file: Union[io.BufferedReader, tuple[str, io.BytesIO, str]], source: str, target: str
    ) -> bytes:
        """
        Translate a file from source to target language.
        :param file:
        :param source:
        :param target:
        :return:
        """

        if isinstance(file, tuple):
            _file = file[1]

            # API fails on empty strings
            content = _file.read()
            _file.seek(0)
            if not content.strip():
                return content

        else:
            # API fails on empty strings
            content = file.read()
            file.seek(0)
            if not content.strip():
                return content

        files = {"file": file}

        url = urllib.parse.urljoin(self.URL, "translate/document/blocking")

        response_translate_file = self.handle_post_request(
            url, files=files, data={"source": source, "target": target}
        )

        return response_translate_file.content

    def handle_post_request(self, url, *args, **kwargs) -> requests.Response:
        try:
            response = requests.post(
                url,
                *args,
                **kwargs,
            )
        except requests.exceptions.ConnectionError as e:
            self.raise_connection_error(info=str(e))

        else:
            if response.status_code == 404:
                self.raise_connection_error(info=response.text)

            if not response.ok:
                raise_response(response)

            return response

    def raise_connection_error(self, info: str):
        message = "CEF ETranslation API not available"
        logger.error(message + " - " + info)
        raise ConnectionError(message)
