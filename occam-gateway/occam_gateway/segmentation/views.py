import logging

from drf_spectacular.utils import extend_schema
from lxml import etree
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response

from organisation.models import OrganisationAPIKey
from shared.models import StatusField
from shared.pipeline import (
    TextParagraphParser,
    PageXMLParagraphParser,
    PageXMLWrapper,
    SegmentationStep,
)
from .connector import SegmentationConnector
from .models import UsageSegmentation
from .serializers import (
    SegmentationSerializer,
    SegmentationFileSerializer,
    SegmentationFileResponseSerializer,
)

logger = logging.getLogger("django")

"""
Acts as a bridge between the Segmentation correction API and the public Django API
"""


@extend_schema(
    description="Text to sentence segmentation pipeline",
)
class SegmentationPipelineAPIView(GenericAPIView):
    """
    Base class for segmentation API views
    """

    parser_classes = [JSONParser]
    serializer_class = SegmentationSerializer

    def post(self, request, *args, **kwargs):
        api_key = OrganisationAPIKey.objects.get_from_request(request)

        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        _text = serializer.validated_data.get("text")
        _language = serializer.validated_data.get("language")

        usage = UsageSegmentation.objects.create(
            api_key=api_key,
            source_size=sum(map(len, _text)),
            source_language=_language,
            status=StatusField.IN_PROGRESS,
        )

        connector = SegmentationConnector()
        options = connector.options

        try:
            seg_response = connector.pipeline(_text, _language, options=options)
        except Exception as e:
            logger.error(f"Segmentation failed: {e}")
            usage.set_status(StatusField.FAILED)
            return Response({"error": "Segmentation failed"}, status=500)

        usage.set_status(StatusField.SUCCESS)
        usage.target_size = sum(map(len, seg_response.lines))
        usage.save()

        return Response({"text": seg_response.lines})


class SegmentationFileAPIView(GenericAPIView):
    """
    (Sentence) Segmentation of PageXML or text files
    """

    parser_classes = [MultiPartParser]
    serializer_class = SegmentationFileSerializer

    @extend_schema(responses=SegmentationFileResponseSerializer)
    def post(self, request, *args, **kwargs):
        api_key = OrganisationAPIKey.objects.get_from_request(request)

        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        _file = serializer.validated_data.get("file")
        _language = serializer.validated_data.get("language")

        # Parse file
        text = self.parse_file(_file)

        usage = UsageSegmentation.objects.create(
            api_key=api_key,
            source_size=len(TextParagraphParser().backward(text).strip()),
            source_language=_language,
            status=StatusField.IN_PROGRESS,
        )

        try:
            step = SegmentationStep(source_lang=_language)
            text_segmented = step.forward(text)
        except Exception as e:
            logger.error(f"Segmentation failed: {e}")
            usage.set_status(StatusField.FAILED)
            return Response({"error": "Segmentation failed"}, status=500)

        flat_text_segmented = TextParagraphParser().backward(text_segmented)

        d = {"text": text_segmented, "file": flat_text_segmented}
        if _language:
            d["language"] = _language

        response_serializer = SegmentationFileResponseSerializer(data=d)
        if not response_serializer.is_valid():
            logger.error(f"Failed to parse results: {response_serializer.errors}")
            usage.set_status(StatusField.FAILED)
            return Response({"error": "Failed to parse results"}, status=500)

        usage.set_status(StatusField.SUCCESS)
        usage.target_size = len(flat_text_segmented.strip())
        usage.save()

        return Response(response_serializer.data)

    def parse_file(self, file):
        """
        Parse the file and return the text content
        """

        if self.check_xml(file):
            # Parse the XML file
            page_xml = PageXMLWrapper()
            page_xml.parse(file)
            return PageXMLParagraphParser().forward(page_xml)
        else:
            page_xml = file.read().decode("utf-8")
            return TextParagraphParser().forward(page_xml)
        # Convert the file to text

        pass

    def check_xml(self, file) -> bool:
        try:
            etree.parse(file)
            return True
        except:
            return False
        finally:
            file.seek(0)
