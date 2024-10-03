import io
import json
import logging
import os
import shutil
import tempfile
from contextlib import contextmanager

from dinglehopper.cli import process
from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from lxml import etree
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response

from .serializers import OCREvalSerializer, OCREvalTextSerializer

logger = logging.getLogger("django")


class OCREvalShared:
    @contextmanager
    def eval_shared(self, file_ocr, file_gt, basename_ocr: str, basename_gt: str):
        tmpdir = tempfile.mkdtemp()
        try:
            temp_ocr_file_path = os.path.join(tmpdir, basename_ocr)
            temp_gt_file_path = os.path.join(tmpdir, basename_gt)

            if temp_gt_file_path == temp_ocr_file_path:
                base, ext = os.path.splitext(basename_ocr)
                temp_gt_file_path = os.path.join(tmpdir, f"{base} (orig){ext}")

            self._create_temp_page(file_ocr, temp_ocr_file_path)
            self._create_temp_page(file_gt, temp_gt_file_path)

            process(
                temp_gt_file_path,
                temp_ocr_file_path,
                report_prefix="report",
                reports_folder=os.path.join(tmpdir, "eval"),
                # metrics=metrics,
                differences=True,
                textequiv_level="line",  # "Region" did not seem to work
            )

            yield tmpdir
        finally:
            shutil.rmtree(tmpdir)

    def _create_page_xml_from_text(self, text: str) -> str:
        root = etree.Element(
            "PcGts",
            {
                "xmlns": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15"
            },
        )

        etree.SubElement(root, "Metadata")
        page = etree.SubElement(root, "Page")
        text_region = etree.SubElement(page, "TextRegion", {"id": "r1"})
        for i, line in enumerate(text.split("\n")):
            text_line = etree.SubElement(
                text_region, "TextLine", {"id": f"r1-l{i + 1}"}
            )
            text_equiv = etree.SubElement(text_line, "TextEquiv")
            unicode = etree.SubElement(text_equiv, "Unicode")
            unicode.text = line

        return etree.tostring(
            root, pretty_print=True, encoding="utf-8", xml_declaration=True
        ).decode("utf-8")

    def _create_temp_page(self, _file, path):
        xml_bytes = _file.read()

        # Check if xml
        try:
            etree.parse(xml_bytes)
        except Exception as e:
            # Not XML, assume text, wrap in XML
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

            with open(report_json_path, "r") as report_json:
                report_dict = json.load(report_json)

        # Clean up the temporary data
        report_dict["gt"] = os.path.basename(report_dict["gt"])
        report_dict["ocr"] = os.path.basename(report_dict["ocr"])

        return Response(report_dict)
