import io
import json
import logging
import os
from contextlib import contextmanager
from tempfile import TemporaryDirectory

from dinglehopper.cli import process
from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from lxml import etree
from lxml.etree import XMLSyntaxError
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response

from .serializers import OCREvalSerializer, OCREvalTextSerializer

logger = logging.getLogger("django")


class OCREvalShared:
    @contextmanager
    def eval_shared(self, file_ocr, file_gt, basename_ocr: str, basename_gt: str):
        """
        Context manager for evaluating OCR files using Dinglehopper.

        Args:
            file_ocr: The OCR file-like object.
            file_gt: The ground truth file-like object.
            basename_ocr: The base name for the OCR file.
            basename_gt: The base name for the ground truth file.
        """
        with TemporaryDirectory() as tmpdir:
            temp_ocr_file_path = os.path.join(tmpdir, basename_ocr)
            temp_gt_file_path = os.path.join(tmpdir, basename_gt)

            if temp_gt_file_path == temp_ocr_file_path:
                base, ext = os.path.splitext(basename_ocr)
                temp_gt_file_path = os.path.join(tmpdir, f"{base} (orig){ext}")

            self._create_temp_page(file_ocr, temp_ocr_file_path)
            self._create_temp_page(file_gt, temp_gt_file_path)

            logger.info(
                f"Evaluating OCR file '{basename_ocr}' against ground truth file '{basename_gt}'."
            )

            process(
                temp_gt_file_path,
                temp_ocr_file_path,
                report_prefix="report",
                reports_folder=os.path.join(tmpdir, "eval"),
                differences=True,
                textequiv_level="line",  # "Region" does not seem to work
            )

            yield tmpdir

    def _create_page_xml_from_text(self, text: str) -> str:
        """
        Converts plain text into PAGE XML format.

        Args:
            text: The plain text to convert.

        Returns:
            A string containing the PAGE XML representation of the text.
        """
        root = etree.Element(
            "PcGts",
            {"xmlns": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15"},
        )

        etree.SubElement(root, "Metadata")
        page = etree.SubElement(root, "Page")
        text_region = etree.SubElement(page, "TextRegion", {"id": "r1"})
        for i, line in enumerate(text.split("\n")):
            text_line = etree.SubElement(
                text_region, "TextLine", {"id": f"r1-l{i + 1}"}
            )
            text_equiv = etree.SubElement(text_line, "TextEquiv")
            unicode_elem = etree.SubElement(text_equiv, "Unicode")
            unicode_elem.text = line

        return etree.tostring(
            root, pretty_print=True, encoding="utf-8", xml_declaration=True
        ).decode("utf-8")

    def _create_temp_page(self, _file, path):
        """
        Creates a temporary PAGE XML file from the given file-like object.

        Args:
            _file: The file-like object containing XML or plain text.
            path: The path where the temporary file will be saved.
        """
        xml_bytes = _file.read()

        try:
            etree.fromstring(xml_bytes)
        except XMLSyntaxError as e:
            logger.debug(f"Input is not valid XML: {e}. Wrapping content in PAGE XML format.")
            xml_bytes = self._create_page_xml_from_text(
                xml_bytes.decode("utf-8")
            ).encode("utf-8")

        with open(path, "wb") as temp_file:
            temp_file.write(xml_bytes)


@extend_schema(
    description="OCR evaluation, powered by [Dinglehopper](https://github.com/qurator-spk/dinglehopper)",
)
class OCREvalAPIView(GenericAPIView, OCREvalShared):
    parser_classes = [MultiPartParser]
    serializer_class = OCREvalSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        _file_ocr = serializer.validated_data.get("file_ocr")
        _file_gt = serializer.validated_data.get("file_gt")

        with self.eval_shared(
                _file_ocr, _file_gt, _file_ocr.name, _file_gt.name
        ) as tmpdir:
            report_file_path = os.path.join(tmpdir, "eval", "report.html")

            logger.info(f"Sending evaluation report: {report_file_path}")

            response = FileResponse(
                open(report_file_path, "rb"),
                as_attachment=True,
                filename=os.path.basename(report_file_path),
            )
            return response


@extend_schema(
    description="OCR evaluation on text, powered by [Dinglehopper](https://github.com/qurator-spk/dinglehopper)",
)
class OCREvalTextAPIView(GenericAPIView, OCREvalShared):
    parser_classes = [MultiPartParser, JSONParser]
    serializer_class = OCREvalTextSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        _text_ocr = serializer.validated_data.get("text_ocr")
        _text_gt = serializer.validated_data.get("text_gt")

        with self.eval_shared(
                io.BytesIO(_text_ocr.encode("utf-8")),
                io.BytesIO(_text_gt.encode("utf-8")),
                "text_ocr.txt",
                "text_gt.txt",
        ) as tmpdir:
            report_json_path = os.path.join(tmpdir, "eval", "report.json")

            logger.info(f"Loading evaluation report: {report_json_path}")

            with open(report_json_path, "r", encoding="utf-8") as report_json:
                report_dict = json.load(report_json)

        # Clean up the temporary data in the report
        report_dict["gt"] = os.path.basename(report_dict["gt"])
        report_dict["ocr"] = os.path.basename(report_dict["ocr"])

        return Response(report_dict)
