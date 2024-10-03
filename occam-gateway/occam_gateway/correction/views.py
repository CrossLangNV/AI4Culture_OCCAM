import io
import logging
import os.path
import tempfile
import traceback
from enum import Enum
from functools import wraps
from typing import Optional, Type, Callable

from django.http import FileResponse, HttpResponse
from drf_spectacular.utils import extend_schema
from lxml import etree
from pydantic import BaseModel
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from occam_gateway import settings
from organisation.models import OrganisationAPIKey
from organisation.permissions import HasOrganisationAPIKey
from shared.models import StatusField
from shared.pipeline import (
    OCRCorrectionLLMStep,
    OCRCorrectionSymSpellFlairStep,
    OCRCorrectionSymSpellStep,
    PageXMLParagraphParser,
    PageXMLWrapper,
    PipelineStep,
    TextParagraphParser,
)
from .connector import CorrectionConnector, CorrectionResponse
from .models import UsageCorrection
from .ocr_correction_manual import OCRCorrectorManual
from .serializers import (
    CorrectionFileSerializer,
    CorrectionOptionsResponseSerializer,
    PostOCRCorrectionLLMSerializer,
    PostOCRCorrectionSerializer, ManualCorrectionSerializer,
)

# logger = logging.getLogger("django")
logger = logging.getLogger(__name__)

logger.info("Django views - correction")

"""
Acts as a bridge between the Post-OCR correction API and the public Django API
"""


def handle_exceptions(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            response_data = {"error": str(e)}
            if settings.DEBUG:
                response_data["stack_trace"] = traceback.format_exc()
            return Response(response_data, status=500)

    return wrapper


class OCRManualCorrectionAPIView(GenericAPIView):
    """
    Correct a PageXML file using a manual transcription
    """

    permission_classes = [HasOrganisationAPIKey]
    serializer_class = ManualCorrectionSerializer
    parser_classes = [MultiPartParser]

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        ocr_file = serializer.validated_data['ocr_file']
        transcription_file = serializer.validated_data['transcription_file']

        try:
            # Read the files
            ocr_file_content = ocr_file.read()
            transcription_file_content = transcription_file.read()

            # Write the uploaded files to temporary files
            with tempfile.NamedTemporaryFile(delete=False) as temp_ocr_file, \
                    tempfile.NamedTemporaryFile(delete=False) as temp_transcription_file, \
                    tempfile.NamedTemporaryFile(delete=False) as temp_out_file:

                temp_ocr_file.write(ocr_file_content)
                temp_transcription_file.write(transcription_file_content)
                temp_ocr_file.close()
                temp_transcription_file.close()

                # Process the correction using the OCRCorrector
                ocr_corrector = OCRCorrectorManual(
                    ocrfilename=temp_ocr_file.name,
                    mantransfilename=temp_transcription_file.name
                )
                ocr_corrector.run(ocrupdatefile=temp_out_file.name)

                # Read the corrected content from the output file
                with open(temp_out_file.name, 'rb') as corrected_file:
                    corrected_content = corrected_file.read()

            # Clean up temporary files
            os.remove(temp_ocr_file.name)
            os.remove(temp_transcription_file.name)
            os.remove(temp_out_file.name)

            # Return the corrected content
            return HttpResponse(corrected_content, content_type='application/xml')

        except Exception as e:
            logger.error(f"OCR correction failed: {e}")
            return Response({'error': 'OCR correction failed'}, status=500)


class CorrectionAPIViewMixin(GenericAPIView):
    """
    Base class for Post-OCR correction API views
    """

    parser_classes = [MultiPartParser]
    serializer_class = PostOCRCorrectionSerializer

    permission_classes = [HasOrganisationAPIKey]

    def __init__(self, correction_method, name, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.correction_method = correction_method
        self.name = name

    def post(self, request, *args, **kwargs):
        api_key = OrganisationAPIKey.objects.get_from_request(request)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        _text = serializer.validated_data.get("text")
        _language = serializer.validated_data.get("language")

        usage = UsageCorrection.objects.create(
            api_key=api_key,
            method=self.name,
            source_size=len(_text),
            source_language=_language,
            status=StatusField.IN_PROGRESS,
        )

        logger.info(f"Correction request")

        try:
            correction = self.correction_method(_text, _language)
        except Exception as e:
            logger.error(f"Correction failed: {e}")
            usage.set_status(StatusField.FAILED)
            return Response({"error": "Correction failed"}, status=500)

        usage.set_status(StatusField.SUCCESS)
        usage.corrected_size = len(correction.text)
        usage.save()

        return Response(correction.dict())


@extend_schema(
    description="Post-OCR correction of text using sym spell",
)
class PostOCRSymSpellAPIView(CorrectionAPIViewMixin):
    """
    Correct OCR output using SymSpell
    """

    def __init__(self, *args, **kwargs):
        correction_method = CorrectionConnector().correct_sym_spell
        super().__init__(correction_method, name="sym_spell", *args, **kwargs)


@extend_schema(
    description="Post-OCR correction of text using sym spell and flair",
)
class PostOCRSymSpellFlairAPIView(CorrectionAPIViewMixin):
    """
    Correct OCR output using SymSpell and flair
    """

    def __init__(self, *args, **kwargs):
        correction_method = CorrectionConnector().correct_sym_spell_flair
        super().__init__(correction_method, name="sym_spell_flair", *args, **kwargs)


@extend_schema(
    description="Post-OCR correction of text using a Large Language Model (LLM)",
)
class PostOCRLLMAPIView(CorrectionAPIViewMixin):
    """
    Correct OCR output using an LLM
    """

    serializer_class = PostOCRCorrectionLLMSerializer

    def __init__(self, *args, **kwargs):
        correction_method = CorrectionConnector().correct_llm
        super().__init__(correction_method, name="llm", *args, **kwargs)

    def post(self, request, *args, **kwargs):
        api_key = OrganisationAPIKey.objects.get_from_request(request)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        _text = serializer.validated_data.get("text")
        _language = serializer.validated_data.get("language")
        _prompt = serializer.validated_data.get("prompt")

        usage = UsageCorrection.objects.create(
            api_key=api_key,
            method=self.name,
            source_size=len(_text),
            source_language=_language,
            extra={"prompt": _prompt} if _prompt else None,
            status=StatusField.IN_PROGRESS,
        )

        try:
            correction = self.correction_method(_text, _language, prompt=_prompt)
        except Exception as e:
            logger.error(f"Correction failed: {e}")
            usage.set_status(StatusField.FAILED)

            # Returning original text
            fail_safe = CorrectionResponse(
                text=_text,
                language=_language,
                info="Correction failed",
            )
            return Response(fail_safe.dict())
            if 0:
                return Response({"error": "Correction failed"}, status=500)

        usage.set_status(StatusField.SUCCESS)
        usage.corrected_size = len(correction.text)
        usage.save()

        return Response(correction.dict())


class CorrectionInfo(BaseModel):
    step_class: Type[PipelineStep]
    name: str
    description: Optional[str]


class CorrectionEnum(Enum):
    SYMSPELL = CorrectionInfo(
        step_class=OCRCorrectionSymSpellStep,
        name="Correction (SymSpell)",
        description="Post-OCR correction using SymSpell",
    )
    SYMSPELL_FLAIR = CorrectionInfo(
        step_class=OCRCorrectionSymSpellFlairStep,
        name="Correction (SymSpell + Flair)",
        description="Post-OCR correction using SymSpell and Flair",
    )
    LLM = CorrectionInfo(
        step_class=OCRCorrectionLLMStep,
        name="Correction (LLM)",
        description="Post-OCR correction using a Large Language Model (LLM)",
    )

    @staticmethod
    def get_representation():
        return [
            {
                "name": step.value.name,
                "description": step.value.description,
            }
            for step in CorrectionEnum
        ]

    @staticmethod
    def get_step_class_from_name(name):
        return next(
            step.value.step_class
            for step in CorrectionEnum
            if step.value.name.lower() == name.lower()
        )


class CorrectionFileAPIView(GenericAPIView):
    parser_classes = [MultiPartParser]
    serializer_class = CorrectionFileSerializer

    def post(self, request, *args, **kwargs):
        api_key = OrganisationAPIKey.objects.get_from_request(request)

        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        _file = serializer.validated_data.get("file")
        _language = serializer.validated_data.get("language")

        # Parse file
        file_text, parser = self.parse_file(_file)

        text = parser.forward(file_text)

        if 0:
            usage = UsageCorrection.objects.create(
                api_key=api_key,
                source_size=len(TextParagraphParser().backward(text).strip()),
                source_language=_language,
                status=StatusField.IN_PROGRESS,
            )

        option = serializer.validated_data.get("option")
        step = CorrectionEnum.get_step_class_from_name(option)(_language)

        try:
            text_corrected = step.forward(text)
        except Exception as e:
            logger.error(f"Segmentation failed: {e}")
            if 0:
                usage.set_status(StatusField.FAILED)
            return Response({"error": "Segmentation failed"}, status=500)

        file_text_segmented = parser.backward(text_corrected)

        if 0:
            usage.set_status(StatusField.SUCCESS)
            usage.target_size = len(flat_text_segmented.strip())
            usage.save()

        buffer = io.BytesIO()
        buffer.write(str(file_text_segmented).encode("utf-8"))
        buffer.seek(0)  # Move the cursor to the beginning of the buffer

        basename, ext = os.path.splitext(os.path.basename(_file.name))
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=f"{basename}_corrected{ext}",
        )

    def parse_file(self, file) -> (str, PipelineStep):
        """
        Parse the file and return the text content
        """

        if self.check_xml(file):
            # Parse the XML file
            page_xml = PageXMLWrapper()
            page_xml.parse(file)
            parser = PageXMLParagraphParser()

        else:
            # Parse as text file
            page_xml = file.read().decode("utf-8")
            parser = TextParagraphParser()

        return page_xml, parser

    def check_xml(self, file) -> bool:
        try:
            etree.parse(file)
            return True
        except:
            return False
        finally:
            file.seek(0)


class CorrectionOptionsAPIView(GenericAPIView):
    """
    Available Post-OCR options
    """

    @extend_schema(responses=CorrectionOptionsResponseSerializer(many=True))
    def get(self, request, *args, **kwargs):
        steps = CorrectionEnum.get_representation()

        serializer = CorrectionOptionsResponseSerializer(data=steps, many=True)

        if not serializer.is_valid():
            return Response(
                {"error": "Unable to retrieve correction options"}, status=500
            )

        return Response(serializer.data)
