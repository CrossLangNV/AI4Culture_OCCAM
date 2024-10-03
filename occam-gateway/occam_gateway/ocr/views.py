import logging
import os
import tempfile
import traceback
from functools import wraps
from io import BytesIO
from typing import Callable
from zipfile import ZipFile

import requests
from celery.result import AsyncResult
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from occam_gateway import settings
from organisation.models import OrganisationAPIKey
from organisation.permissions import HasOrganisationAPIKey
from shared.models import StatusField
from shared.pipeline import PipelineStepEnum
from .models import OCREngine, UsageOCR
from .ocr_correction import OCRCorrector
from .ocr_engine_mapping import get_connector_for_engine
from .ocr_postprocess_xml import add_custom_reading_order
from .serializers import (
    OCREngineSerializer,
    OCRPipelineSerializer,
    UploadFileSerializer,
    UploadURLSerializer, CorrectionSerializer, CombinedUploadURLSerializer, CombinedUploadFileSerializer,
)
from .tasks import process_ocr_url_task, process_ocr_pdf_task, process_ocr_image_task, process_ocr_pipeline_task

logger = logging.getLogger("django")


# Custom exception classes
class ConnectorNotFoundError(Exception):
    pass


class OCRFailedError(Exception):
    pass


class ImageFetchError(Exception):
    pass


class InvalidPipelineOptionsError(Exception):
    pass


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


class OCREngineListView(ListAPIView):
    queryset = OCREngine.objects.all()
    serializer_class = OCREngineSerializer


class OCRHealthCheckAPIView(APIView):
    @extend_schema(description="Check the health of the OCR service")
    def get(self, request, *args, **kwargs):
        try:
            connector = get_connector_for_engine(OCREngine.objects.first())
            connector.health_check()
            return Response({"status": "Healthy"}, status=200)
        except Exception as e:
            logger.error(f"OCR health check failed: {e}")
            return Response({"status": "Unhealthy"}, status=500)


class BaseOCRAPIView(GenericAPIView):
    """
    Base class for OCR API views that process images. Subclasses must implement get_image.
    """

    permission_classes = [HasOrganisationAPIKey]

    def get_image(self, serializer):
        """
        Retrieve the image file to be OCRed. Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement get_image()")

    def get_engine(self, serializer) -> OCREngine:
        """
        Retrieve the OCR engine based on serializer data.
        """
        engine_id = serializer.validated_data.get("engineId")
        try:
            engine = OCREngine.objects.get(pk=engine_id)
            return engine
        except OCREngine.DoesNotExist:
            logger.error(f"OCREngine with id={engine_id} does not exist.")
            raise OCRFailedError(f"OCREngine with id={engine_id} does not exist.")

    def get_connector(self, engine: OCREngine):
        """
        Fetch the appropriate connector for the given OCR engine.
        """
        try:
            return get_connector_for_engine(engine)
        except ValueError as e:
            logger.error(f"OCR connector not properly configured for engine ({engine}): {e}")
            raise ConnectorNotFoundError(f"OCR connector not configured: {e}")

    def ocr_image(self, file: BytesIO, connector, usage=None):
        """
        Process the OCR image and handle failures.
        """
        try:
            return connector.ocr_image(file)
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            if usage:
                usage.set_status(StatusField.FAILED)
            raise OCRFailedError("OCR processing failed") from e

    def create_usage(self, api_key, engine: OCREngine, image_size: int):
        """
        Create a usage entry to track the OCR processing.
        """
        return UsageOCR.objects.create(
            api_key=api_key,
            ocr_engine=engine,
            image_size=image_size,
            status=StatusField.IN_PROGRESS,
        )

    def fail_usage(self, usage, log_message, error_message):
        """
        Log and mark usage as failed.
        """
        logger.error(log_message)
        usage.set_status(StatusField.FAILED)
        return Response({"error": error_message}, status=500)

    def success_response(self, usage, content: str, content_type: str = "text/plain"):
        """
        Handle a successful OCR operation and return the response.
        """
        usage.overlay_size = len(content)
        usage.status = StatusField.SUCCESS
        usage.save()

        return HttpResponse(content, content_type=content_type)


class BaseCombinedOCRAPIView(BaseOCRAPIView):
    """
    Base class for combined OCR views to handle common functionality.
    """

    def get_pipeline_steps(self, options):
        if options is None:
            options = []
        if not options:
            # Default pipeline steps
            options = []
        steps = []
        steps_keys = []
        render_txt = False
        for key in options:
            key = key.upper()
            if key == "RENDER_TXT":
                render_txt = True
            else:
                step_class = PipelineStepEnum.get_by_key(key)
                steps.append(step_class)
                steps_keys.append(key)
        return steps, render_txt, steps_keys

    def handle_async_processing(
            self,
            content: bytes,
            content_type: str,
            engine_id: int,
            options: list,
            serializer=None
    ):
        """
        Handle asynchronous OCR processing based on content type and options.
        """
        if options:
            return self.handle_async_pipeline(content, content_type, engine_id, options, serializer)
        return self.handle_async_file(content, content_type, engine_id)

    def handle_async_pipeline(
            self,
            content: bytes,
            content_type: str,
            engine_id: int,
            options: list,
            serializer=None
    ):
        """
        Handle asynchronous OCR processing with pipeline steps.
        """
        steps, render_txt, steps_keys = self.get_pipeline_steps(options)
        task = process_ocr_pipeline_task.apply_async(
            args=[
                content,
                engine_id,
                steps_keys,
                serializer.validated_data.get("source_lang"),
                render_txt,
                content_type  # Pass content_type to the task
            ]
        )
        return Response({"task_id": task.id, "status": "Processing"}, status=202)

    def handle_async_file(
            self,
            content: bytes,
            content_type: str,
            engine_id: int
    ):
        """
        Handle asynchronous OCR processing for files (images or PDFs).
        """
        task_mapping = {
            'pdf': process_ocr_pdf_task,
            'image': process_ocr_image_task,
            'url': process_ocr_url_task,
        }
        task_func = task_mapping.get(content_type)
        if not task_func:
            logger.error(f"Unsupported content type for async processing: {content_type}")
            raise OCRFailedError(f"Unsupported content type: {content_type}")

        task = task_func.apply_async(args=[content, engine_id])
        return Response({"task_id": task.id, "status": "Processing"}, status=202)

    def handle_sync_processing(
            self,
            content: bytes,
            content_type: str,
            engine_id: int,
            options: list,
            serializer=None
    ):
        """
        Handle synchronous OCR processing based on content type and options.
        """
        try:
            if options:
                return self.handle_sync_pipeline(content, content_type, engine_id, options, serializer)
            return self.handle_sync_file(content, content_type, engine_id)
        except Exception as e:
            return self.handle_sync_error(e)

    def handle_sync_pipeline(
            self,
            content: bytes,
            content_type: str,
            engine_id: int,
            options: list,
            serializer=None
    ):
        """
        Handle synchronous OCR processing with pipeline steps.
        """
        steps, render_txt, steps_keys = self.get_pipeline_steps(options)
        result = process_ocr_pipeline_task(
            content,
            engine_id,
            steps_keys,
            serializer.validated_data.get("source_lang"),
            render_txt,
            content_type  # Pass content_type to the task
        )
        return self.construct_http_response(result)

    def handle_sync_file(
            self,
            content: bytes,
            content_type: str,
            engine_id: int
    ):
        """
        Handle synchronous OCR processing for files (images or PDFs).
        """
        task_mapping = {
            'pdf': process_ocr_pdf_task,
            'image': process_ocr_image_task,
            'url': process_ocr_url_task,
        }
        task_func = task_mapping.get(content_type)
        if not task_func:
            logger.error(f"Unsupported content type for sync processing: {content_type}")
            raise OCRFailedError(f"Unsupported content type: {content_type}")

        result = task_func(content, engine_id)
        return self.construct_http_response(result)

    def handle_sync_error(self, exception: Exception):
        """
        Handle errors during synchronous OCR processing.
        """
        logger.error(f"Synchronous OCR processing failed: {exception}", exc_info=True)
        response_data = {"error": str(exception)}
        if settings.DEBUG:
            response_data["stack_trace"] = traceback.format_exc()
        return Response(response_data, status=500)

    def construct_http_response(self, result: dict):
        """
        Construct an HTTP response based on OCR processing result.
        """
        if isinstance(result, dict) and 'result' in result and 'content_type' in result:
            return HttpResponse(result['result'], content_type=result['content_type'])
        else:
            logger.error("Invalid OCR processing result format.")
            return Response({"error": "Invalid OCR processing result."}, status=500)


class OCRAPIView(BaseOCRAPIView):
    """
    OCR an uploaded image
    """

    parser_classes = [MultiPartParser]
    serializer_class = UploadFileSerializer

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        _file = self.get_image(serializer)
        engine = self.get_engine(serializer)

        file_content = _file.read()

        # Enqueue the OCR job
        task = process_ocr_image_task.apply_async(
            args=[file_content, engine.id]
        )

        return Response({"task_id": task.id, "status": "Processing"}, status=202)

    def get_image(self, serializer):
        _file = serializer.validated_data.get("file")
        self.image_size = _file.size
        return _file


class OCRFromURLAPIView(BaseOCRAPIView):
    """
    OCR an image from a URL
    """

    parser_classes = [MultiPartParser]
    serializer_class = UploadURLSerializer

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        url = serializer.validated_data.get("url")
        engine = self.get_engine(serializer)

        # Enqueue the OCR job
        task = process_ocr_url_task.apply_async(
            args=[url, engine.id]
        )

        return Response({"task_id": task.id, "status": "Processing"}, status=202)

    def get_image(self, serializer):
        url = serializer.validated_data.get("url")
        try:
            response = requests.get(url)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                raise ImageFetchError("URL does not point to an image")
            image_content = response.content
            self.image_size = len(image_content)
            return BytesIO(image_content)
        except requests.RequestException as e:
            logger.error(f"Failed to fetch image from URL: {e}")
            raise ImageFetchError(f"Failed to fetch image from URL: {e}")


class OCRPDFAPIView(BaseOCRAPIView):
    """
    OCR a PDF and return a ZIP of images and XMLs
    """

    parser_classes = [MultiPartParser]
    serializer_class = UploadFileSerializer

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        _file = serializer.validated_data.get("file")
        engine = self.get_engine(serializer)

        file_content = _file.read()

        # Enqueue the OCR job
        task = process_ocr_pdf_task.apply_async(
            args=[file_content, engine.id]
        )

        return Response({"task_id": task.id, "status": "Processing"}, status=202)

    def process_images_to_zip(self, images, connector, _file, usage):
        l_xml = []
        zip_bytes = BytesIO()
        with ZipFile(zip_bytes, "w") as zf:
            for i, image in enumerate(images):
                image_io = BytesIO()
                image.save(image_io, format="PNG")
                image_io.seek(0)
                try:
                    data = connector.ocr_image(image_io)
                except Exception as e:
                    logger.error(f"OCR failed on page {i + 1}: {e}")
                    usage.set_status(StatusField.FAILED)
                    raise OCRFailedError(f"OCR failed on page {i + 1}")
                xml = add_custom_reading_order(data.get("xml"))
                l_xml.append(xml)
                zf.writestr(f"page_{i + 1}.png", image_io.getvalue())
            for i, xml_i in enumerate(l_xml):
                zf.writestr(f"page_{i + 1}.xml", xml_i)
        zip_bytes.seek(0)
        basename = os.path.splitext(_file.name)[0]
        zip_name = f"{basename}.zip"
        return zip_bytes, zip_name

    def return_zip_response(self, zip_bytes, zip_name, usage):
        response = HttpResponse(zip_bytes.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = f"attachment; filename={zip_name}"
        usage.overlay_size = zip_bytes.getbuffer().nbytes
        usage.status = StatusField.SUCCESS
        usage.save()
        return response


class OCRPipelineAPIView(BaseOCRAPIView):
    """
    Submit an image for OCR processing. The OCR pipeline extracts and returns the textual content
    from the provided image.
    """
    parser_classes = [MultiPartParser]
    serializer_class = OCRPipelineSerializer

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        _file = self.get_image(serializer)
        engine = self.get_engine(serializer)
        file_content = _file.read()

        # Prepare task arguments
        options = serializer.validated_data.get("options")
        source_lang = serializer.validated_data.get("source")

        steps, render_txt, steps_keys = self.get_pipeline_steps(options)

        # Enqueue the OCR pipeline job
        task = process_ocr_pipeline_task.apply_async(
            args=[file_content, engine.id, steps_keys, source_lang, render_txt]
        )

        return Response({"task_id": task.id, "status": "Processing"}, status=202)

    def get_image(self, serializer):
        _file = serializer.validated_data["file"]
        self.image_size = _file.size
        return _file

    def get_pipeline_steps(self, options):
        if options is None:
            options = []
        if not options:
            options = ["DEHYPHENATION", "JOIN_PARAGRAPH", "SENTENCE_SEGMENTATION"]
        steps = []
        steps_keys = []
        render_txt = False
        for key in options:
            key = key.upper()
            if key == "RENDER_TXT":
                render_txt = True
            else:
                step_class = PipelineStepEnum.get_by_key(key)
                steps.append(step_class)
                steps_keys.append(key)
        return steps, render_txt, steps_keys


class CombinedOCRAPIView(BaseCombinedOCRAPIView):
    """
    OCR endpoint that handles image uploads, PDF uploads, and optional pipeline processing.
    """
    parser_classes = [MultiPartParser]
    serializer_class = CombinedUploadFileSerializer

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for OCR processing.
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        engine = self.get_engine(serializer)
        options = serializer.validated_data.get("options", [])
        _file = self.get_image(serializer)
        file_content = _file.read()
        file_extension = os.path.splitext(_file.name)[1].lower()
        content_type = 'pdf' if file_extension == '.pdf' else 'image'
        async_param = serializer.validated_data.get("async_param", False)

        # Create usage record
        usage = self.create_usage(
            api_key=OrganisationAPIKey.objects.get_from_request(request),
            engine=engine,
            image_size=_file.size
        )

        if async_param:
            try:
                response = self.handle_async_processing(
                    content=file_content,
                    content_type=content_type,
                    engine_id=engine.id,
                    options=options,
                    serializer=serializer
                )
            except Exception as e:
                return self.fail_usage(usage, str(e), "Failed to initiate OCR processing.")
            return response

        try:
            response = self.handle_sync_processing(
                content=file_content,
                content_type=content_type,
                engine_id=engine.id,
                options=options,
                serializer=serializer
            )
            usage.set_status(StatusField.SUCCESS)
            return response
        except OCRFailedError as e:
            return self.fail_usage(usage, str(e), "OCR processing failed.")

    def get_image(self, serializer):
        """
        Retrieve the uploaded file for OCR processing.
        """
        _file = serializer.validated_data.get("file")
        if not _file:
            logger.error("No file provided in the request.")
            raise ImageFetchError("No file provided.")
        return _file


class CombinedOCRFromURLAPIView(BaseCombinedOCRAPIView):
    """
    OCR endpoint that handles image URLs and optional pipeline processing.
    """
    parser_classes = [MultiPartParser]
    serializer_class = CombinedUploadURLSerializer

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for OCR processing from URLs.
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        engine = self.get_engine(serializer)
        options = serializer.validated_data.get("options", [])
        async_param = serializer.validated_data.get("async_param", False)
        url = serializer.validated_data.get("url")

        # Create usage record
        usage = self.create_usage(
            api_key=OrganisationAPIKey.objects.get_from_request(request),
            engine=engine,
            image_size=0  # Size will be updated after fetching in sync mode
        )

        if async_param:
            try:
                response = self.handle_async_processing(
                    content=url,  # Pass URL as string
                    content_type='url',
                    engine_id=engine.id,
                    options=options,
                    serializer=serializer
                )
            except Exception as e:
                return self.fail_usage(usage, str(e), "Failed to initiate OCR processing.")
            return response

        try:
            # Synchronous processing: fetch the image first
            image_io = self.get_image(url)
            image_content = image_io.read()
            usage.image_size = len(image_content)
            usage.save()

            response = self.handle_sync_processing(
                content=image_content,
                content_type='image',  # Treat fetched URL image as 'image'
                engine_id=engine.id,
                options=options,
                serializer=serializer
            )
            usage.set_status(StatusField.SUCCESS)
            return response
        except OCRFailedError as e:
            return self.fail_usage(usage, str(e), "OCR processing failed.")
        except ImageFetchError as e:
            return self.fail_usage(usage, str(e), "Failed to fetch image from URL.")

    def get_image(self, url: str) -> BytesIO:
        """
        Fetch the image from the provided URL.
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                logger.error(f"URL does not point to an image. Content-Type: {content_type}")
                raise ImageFetchError("URL does not point to an image.")
            image_content = response.content
            self.image_size = len(image_content)
            return BytesIO(image_content)
        except requests.RequestException as e:
            logger.error(f"Failed to fetch image from URL: {e}")
            raise ImageFetchError(f"Failed to fetch image from URL: {e}")


class OCRPipelineOptionsAPIView(GenericAPIView):
    """
    Available options for the pipeline
    """

    permission_classes = [HasOrganisationAPIKey]

    @extend_schema(description="Available pipeline options")
    def get(self, request, *args, **kwargs):
        step_representation = PipelineStepEnum.get_representation()
        return Response(step_representation)


class OCRJobStatusAPIView(APIView):
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
            return Response({"status": task_result.state}, status=200)


class OCRJobResultAPIView(APIView):
    permission_classes = [HasOrganisationAPIKey]

    def get(self, request, task_id, *args, **kwargs):
        task_result = AsyncResult(task_id)
        if task_result.state == 'SUCCESS':
            result_data = task_result.result
            # Log the result for debugging
            logger.debug(f"Task result type: {type(result_data)}")
            logger.debug(f"Task result content: {result_data}")
            if isinstance(result_data, dict):
                result = result_data['result']
                content_type = result_data['content_type']
            else:
                # Handle unexpected formats
                result = result_data
                content_type = 'application/xml'  # Default content type
            return HttpResponse(result, content_type=content_type)
        elif task_result.state == 'FAILURE':
            error_message = str(task_result.result)
            return Response({"status": "Failed", "error": error_message}, status=500)
        elif task_result.state == 'PENDING':
            return Response({"status": "Pending"}, status=202)
        else:
            return Response({"status": task_result.state}, status=202)


class OCRCorrectionAPIView(GenericAPIView):
    """
    Correct a PageXML file using a manual transcription
    """

    permission_classes = [HasOrganisationAPIKey]
    serializer_class = CorrectionSerializer
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
                ocr_corrector = OCRCorrector(
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
