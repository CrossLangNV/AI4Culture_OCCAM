"""
Connector methods to PERO-OCR's API.
"""
import abc
import io
import logging
import os
import urllib.parse

import requests

from gateway_utils.connector_utils import raise_response

LOCAL_PERO = os.environ.get("LOCAL_PERO", "")

logger = logging.getLogger(__name__)


class OcrConnector(abc.ABC):
    @abc.abstractmethod
    def ocr_image(self):
        ...


class LocalOcrConnector(OcrConnector):
    def health_check(self) -> bool:
        """
        Check the health of the OCR service.
        """
        url = urllib.parse.urljoin(LOCAL_PERO, "docs")
        response = requests.get(url, timeout=5)

        if response.status_code != 200:
            raise Exception(f"OCR service returned status code {response.status_code}")

        return True

    def ocr_image(
            self,
            file: io.BufferedReader,
    ) -> dict:
        """
        OCRs a page and return the overlay as a page xml bytestring.

        args:
            file: an image file to be OCR'ed

        Example:
            >> with page.file.open() as file:
            >>    overlay_xml = ocr_image(file)
        """

        files = {"image": file}

        url = urllib.parse.urljoin(LOCAL_PERO, "ocr")
        response_ocr_image = requests.post(
            url,
            files=files,
        )

        if not response_ocr_image.ok:
            raise_response(response_ocr_image)

        return response_ocr_image.json()

    def ocr_image_to_PAGE(self, file) -> bytes:
        """
        OCR the text as PAGE xml from an image file.
        """
        return self.ocr_image(file)["xml"].encode()

    def ocr_image_to_text(self, file) -> str:
        """
        OCR the text from an image file.
        """
        d = self.ocr_image(file)

        return d["text"]
