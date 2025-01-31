import io
import logging
import os
import os.path
import re
import tempfile
import traceback
from functools import wraps
from typing import Callable
from xml.etree.ElementTree import ParseError

from celery.result import AsyncResult
from django.http import FileResponse, HttpResponse
from drf_spectacular.utils import extend_schema
from lxml import etree
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from occam_gateway import settings
from ocr.pagexml2geojson import main_from_xml_string
from organisation.models import OrganisationAPIKey
from organisation.permissions import HasOrganisationAPIKey
from shared.models import StatusField
from shared.pipeline import (
    PageXMLParagraphParser,
    PageXMLWrapper,
    PipelineStep,
    TextParagraphParser,
)
from .connector import CorrectionConnector, CorrectionResponse
from .enums import CorrectionEnum
from .models import UsageCorrection
from .ocr_correction_manual import OCRCorrectorManual
from .serializers import (
    CorrectionFileSerializer,
    CorrectionOptionsResponseSerializer,
    PostOCRCorrectionLLMSerializer,
    PostOCRCorrectionSerializer,
    ManualCorrectionSerializer,
    ManualCorrectionStringSerializer,
)
from .tasks import manual_correction_task, manual_correction_string_task, manual_correction_geojson_task, \
    post_ocr_correction_task, correction_file_geojson_task

logger = logging.getLogger(__name__)
logger.info("Django views - correction")


def handle_exceptions(func: Callable):
    """
    A decorator to uniformly catch and log exceptions,
    returning a JSON response with 500 on errors.
    """

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


# ------------------------------------------------------------------------------
#  ASYNC STATUS & RESULT ENDPOINTS
# ------------------------------------------------------------------------------

class CorrectionJobStatusAPIView(GenericAPIView):
    """
    Poll the status of a Celery-based correction job
    """
    permission_classes = [HasOrganisationAPIKey]

    def get(self, request, task_id, *args, **kwargs):
        task_result = AsyncResult(task_id)
        if task_result.state == 'PENDING':
            return Response({"status": "Pending"}, status=200)
        elif task_result.state == 'SUCCESS':
            return Response({"status": "Completed"}, status=200)
        elif task_result.state == 'FAILURE':
            return Response({"status": "Failed", "error": str(task_result.result)}, status=500)
        else:
            # e.g. STARTED, RETRY, etc.
            return Response({"status": task_result.state}, status=200)


class CorrectionJobResultAPIView(GenericAPIView):
    """
    Retrieve the final result of a Celery-based correction job
    """
    permission_classes = [HasOrganisationAPIKey]

    def get(self, request, task_id, *args, **kwargs):
        task_result = AsyncResult(task_id)
        if task_result.state == 'SUCCESS':
            result_data = task_result.result
            if isinstance(result_data, dict):
                content = result_data.get('result', '')
                content_type = result_data.get('content_type', 'text/plain')
            else:
                # If the task returned some unexpected format, fallback:
                content = str(result_data)
                content_type = 'text/plain'
            return HttpResponse(content, content_type=content_type)

        elif task_result.state == 'FAILURE':
            return Response({"status": "Failed", "error": str(task_result.result)}, status=500)
        elif task_result.state == 'PENDING':
            return Response({"status": "Pending"}, status=202)
        else:
            # e.g. STARTED, RETRY, etc.
            return Response({"status": task_result.state}, status=202)


# ------------------------------------------------------------------------------
#  MANUAL CORRECTION: FILE-BASED
# ------------------------------------------------------------------------------

class OCRManualCorrectionAPIView(GenericAPIView):
    """
    Correct a PageXML file using a manual transcription.
    Supports both sync and async correction based on `async_param`.
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
        async_param = serializer.validated_data.get('async_param', False)

        # Additional correction parameters
        params = {
            'ngramlen': serializer.validated_data.get('ngram_len'),
            'maxdistprop': serializer.validated_data.get('max_dist_prop'),
            'maxdistword': serializer.validated_data.get('max_dist_word'),
            'minwordsim': serializer.validated_data.get('min_word_sim'),
            'minwordsimstrong': serializer.validated_data.get('min_word_sim_strong'),
            'maxngrammulti': serializer.validated_data.get('max_ngram_multi'),
            'maxdistunlinked': serializer.validated_data.get('max_dist_unlinked'),
            'xmllogchanges': serializer.validated_data.get('xml_log_changes'),
        }
        params = {k: v for k, v in params.items() if v is not None}

        # Create a UsageCorrection record
        api_key = OrganisationAPIKey.objects.get_from_request(request)
        usage = UsageCorrection.objects.create(
            api_key=api_key,
            method="manual_correction",
            source_size=ocr_file.size + transcription_file.size,
            status=StatusField.IN_PROGRESS,
        )

        if async_param:
            # Asynchronous
            file_bytes_ocr = ocr_file.read()
            file_bytes_transcription = transcription_file.read()

            task = manual_correction_task.apply_async(
                args=[usage.id, file_bytes_ocr, file_bytes_transcription, params]
            )
            return Response({"task_id": task.id, "status": "Processing"}, status=202)

        # ---------------------
        # Synchronous approach
        # ---------------------
        try:
            ocr_file_content = ocr_file.read()
            transcription_file_content = transcription_file.read()

            with tempfile.NamedTemporaryFile(delete=False) as temp_ocr_file, \
                    tempfile.NamedTemporaryFile(delete=False) as temp_transcription_file, \
                    tempfile.NamedTemporaryFile(delete=False) as temp_out_file:

                temp_ocr_file.write(ocr_file_content)
                temp_transcription_file.write(transcription_file_content)
                temp_ocr_file.close()
                temp_transcription_file.close()

                # Process the correction
                ocr_corrector = OCRCorrectorManual(
                    ocrfilename=temp_ocr_file.name,
                    manfilename=temp_transcription_file.name,
                    **params
                )
                ocr_corrector.run(ocrupdatefile=temp_out_file.name)

                with open(temp_out_file.name, 'rb') as corrected_file:
                    corrected_content = corrected_file.read()

            # Clean up
            os.remove(temp_ocr_file.name)
            os.remove(temp_transcription_file.name)
            os.remove(temp_out_file.name)

            usage.set_status(StatusField.SUCCESS)
            usage.corrected_size = len(corrected_content)
            usage.save()

            return HttpResponse(corrected_content, content_type='application/xml')

        except Exception as e:
            logger.error(f"OCR correction failed: {e}", exc_info=True)
            usage.set_status(StatusField.FAILED)
            return Response({'error': 'OCR correction failed'}, status=500)


# ------------------------------------------------------------------------------
#  MANUAL CORRECTION: STRING-BASED
# ------------------------------------------------------------------------------

class OCRManualCorrectionStringInputAPIView(GenericAPIView):
    """
    Correct a PageXML file (as string) using a manual transcription (also as string).
    Supports sync/async via `async_param`.
    """

    permission_classes = [HasOrganisationAPIKey]
    serializer_class = ManualCorrectionStringSerializer

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        ocr_content = serializer.validated_data["ocr"]
        transcription_content = serializer.validated_data["transcription"]
        async_param = serializer.validated_data.get("async_param", False)

        ngram_len = serializer.validated_data.get("ngram_len")
        max_dist_prop = serializer.validated_data.get("max_dist_prop")
        max_dist_word = serializer.validated_data.get("max_dist_word")
        min_word_sim = serializer.validated_data.get("min_word_sim")
        min_word_sim_strong = serializer.validated_data.get("min_word_sim_strong")
        max_ngram_multi = serializer.validated_data.get("max_ngram_multi")
        max_dist_unlinked = serializer.validated_data.get("max_dist_unlinked")
        xml_log_changes = serializer.validated_data.get("xml_log_changes")

        # Create usage
        api_key = OrganisationAPIKey.objects.get_from_request(request)
        usage = UsageCorrection.objects.create(
            api_key=api_key,
            method="manual_correction_string",
            source_size=len(ocr_content) + len(transcription_content),
            status=StatusField.IN_PROGRESS,
        )

        if async_param:
            # Asynchronous
            params = {
                "ngramlen": ngram_len,
                "maxdistprop": max_dist_prop,
                "maxdistword": max_dist_word,
                "minwordsim": min_word_sim,
                "minwordsimstrong": min_word_sim_strong,
                "maxngrammulti": max_ngram_multi,
                "maxdistunlinked": max_dist_unlinked,
                "xmllogchanges": xml_log_changes,
            }
            params = {k: v for k, v in params.items() if v is not None}

            task = manual_correction_string_task.apply_async(
                args=[usage.id, ocr_content, transcription_content, params]
            )
            return Response({"task_id": task.id, "status": "Processing"}, status=202)

        # ---------------------
        # Synchronous approach
        # ---------------------
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp_ocr_file, \
                    tempfile.NamedTemporaryFile(delete=False) as temp_transcription_file, \
                    tempfile.NamedTemporaryFile(delete=False) as temp_out_file:

                # Write input strings to temp files
                temp_ocr_file.write(ocr_content.encode("utf-8"))
                temp_transcription_file.write(transcription_content.encode("utf-8"))
                temp_ocr_file.close()
                temp_transcription_file.close()

                # Build parameters, excluding None
                params = {
                    "ocrfilename": temp_ocr_file.name,
                    "manfilename": temp_transcription_file.name,
                    "ngramlen": ngram_len,
                    "maxdistprop": max_dist_prop,
                    "maxdistword": max_dist_word,
                    "minwordsim": min_word_sim,
                    "minwordsimstrong": min_word_sim_strong,
                    "maxngrammulti": max_ngram_multi,
                    "maxdistunlinked": max_dist_unlinked,
                    "xmllogchanges": xml_log_changes,
                }
                params = {k: v for k, v in params.items() if v is not None}

                # Run correction
                ocr_corrector = OCRCorrectorManual(**params)
                ocr_corrector.run(ocrupdatefile=temp_out_file.name)

                # Read corrected content
                with open(temp_out_file.name, "rb") as corrected_file:
                    corrected_content = corrected_file.read()

            # Clean up
            os.remove(temp_ocr_file.name)
            os.remove(temp_transcription_file.name)
            os.remove(temp_out_file.name)

            usage.set_status(StatusField.SUCCESS)
            usage.corrected_size = len(corrected_content)
            usage.save()

            return HttpResponse(corrected_content, content_type="application/xml")

        except ParseError as parse_err:
            # Specifically catch XML parse errors
            logger.error("XML parse error in OCR correction: %s", parse_err, exc_info=True)
            usage.set_status(StatusField.FAILED)
            return Response(
                {
                    "error": "XML Parse Error",
                    "detail": str(parse_err),
                    "hint": "Ensure your XML is well-formed. Special characters such as '&' must be escaped."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error("OCR correction failed: %s", e, exc_info=True)
            usage.set_status(StatusField.FAILED)
            return Response(
                {"error": "OCR correction failed", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ------------------------------------------------------------------------------
#  MANUAL CORRECTION: GEOJSON RETURN
# ------------------------------------------------------------------------------

class OCRManualCorrectionGeoJsonAPIView(GenericAPIView):
    """
    Correct a PageXML file using a manual transcription,
    then return { text, geojson, pagexml } as JSON.
    Supports sync/async via `async_param`.
    """

    permission_classes = [HasOrganisationAPIKey]
    serializer_class = ManualCorrectionSerializer
    parser_classes = [MultiPartParser]

    def _split_into_sentences(self, text):
        """
        Splits text into sentences using a regular expression.
        """
        sentence_endings = re.compile(r'(?<=[.!?])\s+')
        return sentence_endings.split(text.strip())

    def _xml2sentences(self, xml_str: str) -> str:
        """
        Helper function to parse XML and extract paragraphs -> sentences.
        """
        try:
            parser = etree.XMLParser(recover=True)
            root = etree.fromstring(xml_str.encode('utf-8'), parser=parser)
        except etree.XMLSyntaxError as e:
            logger.error(f"XML parsing error: {e}", exc_info=True)
            return ""

        paragraphs = []
        paragraph_elements = root.xpath('//p')
        if not paragraph_elements:
            # If no <p> tags, use all text
            paragraphs.append(''.join(root.itertext()))
        else:
            for elem in paragraph_elements:
                paragraphs.append(''.join(elem.itertext()))

        sentences_all = []
        for paragraph in paragraphs:
            try:
                sentences = self._split_into_sentences(paragraph)
            except Exception as e:
                logger.error(f"Sentence segmentation failed: {e}", exc_info=True)
                sentences = [paragraph]
            sentences_all.extend(sentences)

        return "\n".join(sentences_all)

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        ocr_file = serializer.validated_data['ocr_file']
        transcription_file = serializer.validated_data['transcription_file']
        async_param = serializer.validated_data.get('async_param', False)

        # Additional correction parameters
        params = {
            'ngramlen': serializer.validated_data.get('ngram_len'),
            'maxdistprop': serializer.validated_data.get('max_dist_prop'),
            'maxdistword': serializer.validated_data.get('max_dist_word'),
            'minwordsim': serializer.validated_data.get('min_word_sim'),
            'minwordsimstrong': serializer.validated_data.get('min_word_sim_strong'),
            'maxngrammulti': serializer.validated_data.get('max_ngram_multi'),
            'maxdistunlinked': serializer.validated_data.get('max_dist_unlinked'),
            'xmllogchanges': serializer.validated_data.get('xml_log_changes'),
        }
        params = {k: v for k, v in params.items() if v is not None}

        api_key = OrganisationAPIKey.objects.get_from_request(request)
        usage = UsageCorrection.objects.create(
            api_key=api_key,
            method="manual_correction_geojson",
            source_size=ocr_file.size + transcription_file.size,
            status=StatusField.IN_PROGRESS,
        )

        if async_param:
            # Asynchronous
            ocr_bytes = ocr_file.read()
            trans_bytes = transcription_file.read()

            task = manual_correction_geojson_task.apply_async(
                args=[usage.id, ocr_bytes, trans_bytes, params]
            )
            return Response({"task_id": task.id, "status": "Processing"}, status=202)

        # ---------------------
        # Synchronous approach
        # ---------------------
        try:
            ocr_file_content = ocr_file.read()
            transcription_file_content = transcription_file.read()

            with tempfile.NamedTemporaryFile(delete=False) as temp_ocr_file, \
                    tempfile.NamedTemporaryFile(delete=False) as temp_transcription_file, \
                    tempfile.NamedTemporaryFile(delete=False) as temp_out_file:

                temp_ocr_file.write(ocr_file_content)
                temp_transcription_file.write(transcription_file_content)
                temp_ocr_file.close()
                temp_transcription_file.close()

                ocr_corrector = OCRCorrectorManual(
                    ocrfilename=temp_ocr_file.name,
                    manfilename=temp_transcription_file.name,
                    **params
                )
                ocr_corrector.run(ocrupdatefile=temp_out_file.name)

                with open(temp_out_file.name, 'rb') as corrected_file:
                    corrected_content = corrected_file.read()

            os.remove(temp_ocr_file.name)
            os.remove(temp_transcription_file.name)
            os.remove(temp_out_file.name)

            # Build the JSON response: text, geojson, pagexml
            corrected_xml_str = corrected_content.decode('utf-8')
            sentences = self._xml2sentences(corrected_xml_str)
            geojson = main_from_xml_string(corrected_xml_str)

            usage.set_status(StatusField.SUCCESS)
            usage.corrected_size = len(corrected_content)
            usage.save()

            return Response({
                "text": sentences,
                "geojson": geojson,
                "pagexml": corrected_xml_str
            })

        except Exception as e:
            logger.error(f"OCR correction failed: {e}", exc_info=True)
            usage.set_status(StatusField.FAILED)
            return Response({'error': 'OCR correction failed'}, status=500)


# ------------------------------------------------------------------------------
#  BASE MIXIN FOR POST-OCR CORRECTION
# ------------------------------------------------------------------------------

class CorrectionAPIViewMixin(GenericAPIView):
    """
    Base class for Post-OCR correction API views (SymSpell, Flair, LLM).
    By default: synchronous. We add `async_param` to let user run asynchronously if desired.
    """

    parser_classes = [MultiPartParser]
    serializer_class = PostOCRCorrectionSerializer
    permission_classes = [HasOrganisationAPIKey]

    def __init__(self, correction_method, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.correction_method = correction_method
        self.name = name

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        _text = serializer.validated_data.get("text")
        _language = serializer.validated_data.get("language")
        async_param = serializer.validated_data.get("async_param", False)

        # Create usage
        api_key = OrganisationAPIKey.objects.get_from_request(request)
        usage = UsageCorrection.objects.create(
            api_key=api_key,
            method=self.name,
            source_size=len(_text),
            source_language=_language,
            status=StatusField.IN_PROGRESS,
        )

        if async_param:
            # Asynchronous (launch Celery task)
            task = post_ocr_correction_task.apply_async(
                args=[usage.id, _text, _language, self.name]
            )
            return Response({"task_id": task.id, "status": "Processing"}, status=202)

        # ---------------------
        # Synchronous approach
        # ---------------------
        try:
            correction = self.correction_method(_text, _language)
            usage.set_status(StatusField.SUCCESS)
            usage.corrected_size = len(correction.text)
            usage.save()
            return Response(correction.dict())
        except Exception as e:
            logger.error(f"Correction failed: {e}", exc_info=True)
            usage.set_status(StatusField.FAILED)
            return Response({"error": "Correction failed"}, status=500)


@extend_schema(description="Post-OCR correction of text using sym spell")
class PostOCRSymSpellAPIView(CorrectionAPIViewMixin):
    """
    Correct OCR output using SymSpell (sync or async).
    """

    def __init__(self, *args, **kwargs):
        correction_method = CorrectionConnector().correct_sym_spell
        super().__init__(correction_method, name="sym_spell", *args, **kwargs)


@extend_schema(description="Post-OCR correction of text using sym spell and flair")
class PostOCRSymSpellFlairAPIView(CorrectionAPIViewMixin):
    """
    Correct OCR output using SymSpell + Flair (sync or async).
    """

    def __init__(self, *args, **kwargs):
        correction_method = CorrectionConnector().correct_sym_spell_flair
        super().__init__(correction_method, name="sym_spell_flair", *args, **kwargs)


# ------------------------------------------------------------------------------
#  LLM Correction (custom prompt)
# ------------------------------------------------------------------------------

@extend_schema(description="Post-OCR correction of text using a Large Language Model (LLM)")
class PostOCRLLMAPIView(CorrectionAPIViewMixin):
    """
    Correct OCR output using an LLM; optionally supply a 'prompt'.
    """
    serializer_class = PostOCRCorrectionLLMSerializer

    def __init__(self, *args, **kwargs):
        correction_method = CorrectionConnector().correct_llm
        super().__init__(correction_method, name="llm", *args, **kwargs)

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        _text = serializer.validated_data.get("text")
        _language = serializer.validated_data.get("language")
        _prompt = serializer.validated_data.get("prompt")
        async_param = serializer.validated_data.get("async_param", False)

        api_key = OrganisationAPIKey.objects.get_from_request(request)
        usage = UsageCorrection.objects.create(
            api_key=api_key,
            method=self.name,  # "llm"
            source_size=len(_text),
            source_language=_language,
            extra={"prompt": _prompt} if _prompt else None,
            status=StatusField.IN_PROGRESS,
        )

        if async_param:
            # Async approach
            task = post_ocr_correction_task.apply_async(
                args=[usage.id, _text, _language, self.name, _prompt]
            )
            return Response({"task_id": task.id, "status": "Processing"}, status=202)

        # ---------------------
        # Synchronous approach
        # ---------------------
        try:
            correction = self.correction_method(_text, _language, prompt=_prompt)
            usage.set_status(StatusField.SUCCESS)
            usage.corrected_size = len(correction.text)
            usage.save()
            return Response(correction.dict())

        except Exception as e:
            logger.error(f"Correction failed: {e}", exc_info=True)
            usage.set_status(StatusField.FAILED)
            # Return original text as fallback
            fail_safe = CorrectionResponse(
                text=_text,
                language=_language,
                info="Correction failed"
            )
            return Response(fail_safe.dict())


# ------------------------------------------------------------------------------
#  FILE-BASED CORRECTION
# ------------------------------------------------------------------------------

class CorrectionFileAPIView(GenericAPIView):
    """
    Example endpoint to upload a file (text or PageXML), parse it,
    run a correction step (SymSpell, Flair, LLM?), then return a corrected file.
    Currently synchronous. You can add async_param if desired.
    """

    parser_classes = [MultiPartParser]
    serializer_class = CorrectionFileSerializer
    permission_classes = [HasOrganisationAPIKey]

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        api_key = OrganisationAPIKey.objects.get_from_request(request)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        _file = serializer.validated_data.get("file")
        _language = serializer.validated_data.get("language")
        option = serializer.validated_data.get("option")
        # Could also read async_param if you wanted to do an async approach

        # parse the input file (either XML or plain text)
        file_text, parser_step = self.parse_file(_file)
        text_segments = parser_step.forward(file_text)

        # (Optional) create usage if you want to track
        # usage = UsageCorrection.objects.create(
        #     api_key=api_key,
        #     method=f"file_correction_{option}",
        #     source_size=_file.size,
        #     source_language=_language,
        #     status=StatusField.IN_PROGRESS,
        # )

        # Determine which pipeline step to use based on "option"
        step_class = CorrectionEnum.get_step_class_from_name(option)
        step_instance = step_class(_language)

        try:
            # Run correction
            text_corrected = step_instance.forward(text_segments)
            file_text_corrected = parser_step.backward(text_corrected)

            buffer = io.BytesIO()
            buffer.write(str(file_text_corrected).encode("utf-8"))
            buffer.seek(0)
            basename, ext = os.path.splitext(os.path.basename(_file.name))

            # if usage:
            #     usage.set_status(StatusField.SUCCESS)
            #     usage.corrected_size = len(file_text_corrected)
            #     usage.save()

            return FileResponse(
                buffer,
                as_attachment=True,
                filename=f"{basename}_corrected{ext}",
            )

        except Exception as e:
            logger.error(f"File correction failed: {e}", exc_info=True)
            # if usage:
            #     usage.set_status(StatusField.FAILED)
            return Response({"error": "File correction failed"}, status=500)

    def parse_file(self, uploaded_file) -> (str, PipelineStep):
        """
        If it's valid XML, parse as PageXML; else parse as text.
        Return (content_str, parser_step).
        """
        # Make sure to read the file's contents fully first
        file_bytes = uploaded_file.read()
        uploaded_file.seek(0)  # reset pointer

        # Try to parse as XML
        if self.is_xml(file_bytes):
            page_xml = PageXMLWrapper()
            # parse the in-memory bytes
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(file_bytes)
                tmp.flush()
                tmp.seek(0)
                page_xml.parse(tmp.name)
            parser = PageXMLParagraphParser()
            return str(page_xml), parser
        else:
            # parse as plain text
            text_str = file_bytes.decode("utf-8", errors="replace")
            parser = TextParagraphParser()
            return text_str, parser

    def is_xml(self, file_bytes: bytes) -> bool:
        """
        Attempt to parse as XML with lxml or stdlib to detect.
        """
        try:
            etree.fromstring(file_bytes)
            return True
        except Exception:
            return False


@extend_schema(
    description="Process an uploaded file (text or PageXML), perform a correction step, "
                "and return {text, geojson, pagexml} as JSON."
)
class CorrectionFileGeoJsonAPIView(GenericAPIView):
    """
    Similar to CorrectionFileAPIView, but instead of returning a corrected file,
    returns a JSON with 'text', 'geojson', and 'pagexml'.
    """

    parser_classes = [MultiPartParser]
    serializer_class = CorrectionFileSerializer
    permission_classes = [HasOrganisationAPIKey]

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        _file = serializer.validated_data.get("file")
        _language = serializer.validated_data.get("language") or ""
        option = serializer.validated_data.get("option")  # e.g. "Correction (SymSpell)"
        async_param = serializer.validated_data.get("async_param", False)

        # (1) Create a UsageCorrection record if you want to track usage
        api_key = OrganisationAPIKey.objects.get_from_request(request)
        usage = UsageCorrection.objects.create(
            api_key=api_key,
            method=f"file_geojson_{option}",
            source_size=_file.size,
            source_language=_language,
            status=StatusField.IN_PROGRESS,
        )

        # (2) Check if we want to do async or sync
        if async_param:
            # --------------------------------------------
            #  ASYNC PATH: Enqueue a Celery task
            # --------------------------------------------
            file_bytes = _file.read()
            task = correction_file_geojson_task.apply_async(
                args=[usage.id, file_bytes, _language, option]
            )
            return Response({"task_id": task.id, "status": "Processing"}, status=202)

        # --------------------------------------------
        #  SYNC PATH:  Do the correction inline
        # --------------------------------------------
        try:
            file_bytes = _file.read()
            # parse the file -> text or pagexml
            is_pagexml, original_content, parser_step = self.parse_file(file_bytes)

            # figure out which step class from the 'option'
            step_class = CorrectionEnum.get_step_class_from_name(option)
            step_instance = step_class(_language)

            # forward -> correct -> backward
            parsed_segments = parser_step.forward(original_content)
            corrected_segments = step_instance.forward(parsed_segments)
            corrected_str = parser_step.backward(corrected_segments)

            # if the file was pagexml, we can produce geojson from corrected_str
            # otherwise, it's just text, so geojson would be empty or None
            text_result = ""
            geojson_result = {}
            pagexml_result = corrected_str  # fallback

            if is_pagexml:
                # create geojson + text from the final corrected XML
                text_result = self._xml2sentences(corrected_str)
                geojson_result = main_from_xml_string(corrected_str)
            else:
                # Not XML => treat corrected_str as plain text
                text_result = corrected_str
                geojson_result = {}

            usage.set_status(StatusField.SUCCESS)
            usage.corrected_size = len(corrected_str)
            usage.save()

            return Response({
                "text": text_result,
                "geojson": geojson_result,
                "pagexml": corrected_str,
            })

        except Exception as e:
            logger.error(f"File geojson correction failed: {e}", exc_info=True)
            usage.set_status(StatusField.FAILED)
            return Response({"error": str(e)}, status=500)

    def parse_file(self, file_bytes: bytes):
        """
        Determine if the file is PageXML or text.
        Returns (is_pagexml, original_content_str, parser_step).
        """
        try:
            etree.fromstring(file_bytes)
            # If no error => it's valid XML => parse as PageXML
            is_pagexml = True
            page_xml = PageXMLWrapper()

            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(file_bytes)
                tmp.flush()
                tmp.seek(0)
                page_xml.parse(tmp.name)

            parser = PageXMLParagraphParser()
            return (True, str(page_xml), parser)

        except Exception:
            # Fallback => treat as text
            is_pagexml = False
            text_str = file_bytes.decode("utf-8", errors="replace")
            parser = TextParagraphParser()
            return (False, text_str, parser)

    def _xml2sentences(self, xml_str: str) -> str:
        """
        Mimics approach of extracting text from PageXML and splitting into sentences.
        """
        try:
            parser = etree.XMLParser(recover=True)
            root = etree.fromstring(xml_str.encode('utf-8'), parser=parser)
        except etree.XMLSyntaxError as e:
            logger.error(f"XML parsing error: {e}", exc_info=True)
            return ""

        # collect paragraphs
        paragraph_elements = root.xpath('//p')
        paragraphs = []
        if not paragraph_elements:
            # fallback: all text
            paragraphs.append(''.join(root.itertext()))
        else:
            for elem in paragraph_elements:
                paragraphs.append(''.join(elem.itertext()))

        # split paragraphs into sentences
        all_sentences = []
        sentence_endings = re.compile(r'(?<=[.!?])\s+')
        for paragraph in paragraphs:
            try:
                splitted = sentence_endings.split(paragraph.strip())
                all_sentences.extend(splitted)
            except Exception as e:
                logger.error(f"Sentence segmentation error: {e}", exc_info=True)
                all_sentences.append(paragraph)

        return "\n".join(all_sentences)


# ------------------------------------------------------------------------------
#  CORRECTION OPTIONS (SYMSPELL, FLAIR, LLM, ETC.)
# ------------------------------------------------------------------------------

class CorrectionOptionsAPIView(GenericAPIView):
    """
    Available Post-OCR correction options
    """

    @extend_schema(responses=CorrectionOptionsResponseSerializer(many=True))
    def get(self, request, *args, **kwargs):
        steps = CorrectionEnum.get_representation()
        serializer = CorrectionOptionsResponseSerializer(data=steps, many=True)
        if not serializer.is_valid():
            return Response(
                {"error": "Unable to retrieve correction options"},
                status=500
            )
        return Response(serializer.data)
