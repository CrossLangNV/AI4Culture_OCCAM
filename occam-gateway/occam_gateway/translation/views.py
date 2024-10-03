import logging
import os
import tempfile
import traceback
import zipfile
from functools import wraps
from typing import Callable

from celery import chord
from celery.result import AsyncResult
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from occam_gateway import settings
from organisation.models import OrganisationAPIKey
from organisation.permissions import HasOrganisationAPIKey
from shared.models import StatusField
from shared.pipeline import PipelineStepEnum
from .connector import CEFETranslationConnector
from .models import UsageTranslationSnippet, UsageTranslationFile
from .serializers import (
    TranslateSnippetSerializer,
    TranslateFileSerializer,
    TranslatePipelineSerializer, CombinedTranslateFileSerializer, CombinedTranslateBatchSerializer,
    CombinedTranslateSnippetSerializer,
)
from .tasks import translate_file_task, translate_pipeline_task, aggregate_translation_results

logger = logging.getLogger("django")


# Custom exception classes
class ConnectorNotFoundError(Exception):
    pass


class TranslationFailedError(Exception):
    pass


class InvalidPipelineOptionsError(Exception):
    pass


def handle_exceptions(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except UnicodeDecodeError as e:
            logger.error(f"Unicode decoding error: {e}", exc_info=True)
            response_data = {"error": "Failed to decode the file. Please ensure it is properly encoded."}
            if settings.DEBUG:
                response_data["details"] = str(e)
            return Response(response_data, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            response_data = {"error": str(e)}
            if settings.DEBUG:
                response_data["stack_trace"] = traceback.format_exc()
            return Response(response_data, status=500)

    return wrapper


class BaseTranslationAPIView(GenericAPIView):
    """
    Base class for Translation API views that handle common functionalities.
    """

    permission_classes = [HasOrganisationAPIKey]

    def get_api_key(self, request):
        """Retrieve the OrganisationAPIKey from the request."""
        return OrganisationAPIKey.objects.get_from_request(request)

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


# Base class for shared functionality between translation views
class CombinedBaseTranslationAPIView(BaseTranslationAPIView):
    """
    Base class for combined translation views to handle common functionality.
    """

    def handle_async_translate(self, usage_id: int, file_content: bytes, source: str, target: str,
                               file_name: str = None, steps_keys: list = None, render_txt: bool = False):
        """
        Handle asynchronous translation using either file or pipeline tasks.
        """
        if steps_keys:
            # Use pipeline task
            task = translate_pipeline_task.apply_async(
                args=[file_content, source, target, steps_keys, render_txt]
            )
        else:
            # Use simple file translation task
            task = translate_file_task.apply_async(
                args=[usage_id, file_content, source, target, file_name]
            )
        return Response({"task_id": task.id, "status": "Processing"}, status=202)

    def handle_sync_translate(self, usage_id: int, file_content: bytes, source: str, target: str,
                              file_name: str = None, steps_keys: list = None, render_txt: bool = False):
        """
        Handle synchronous translation using either file or pipeline tasks.
        """
        try:
            if steps_keys:
                # Use pipeline task
                result = translate_pipeline_task(file_content, source, target, steps_keys, render_txt)
            else:
                # Use simple file translation task
                result = translate_file_task(usage_id, file_content, source, target, file_name)
            return self.construct_http_response(result)
        except Exception as e:
            return self.handle_sync_error(e)

    def handle_async_aggregate_results(self, tasks: list, usage_id: int):
        """
        Handle asynchronous translation tasks and aggregate results.
        """
        # Define the callback task with usage_id
        callback_task = aggregate_translation_results.s(usage_id=usage_id)

        # Create a chord and apply it
        chord_result = chord(tasks)(callback_task)
        logger.info(f"Chord initiated with callback task ID: {chord_result.id} for usage_id={usage_id}")

        # Return the callback_task.id (which is chord_result.id) to the user
        return Response({"task_id": chord_result.id, "status": "Processing"}, status=202)

    def handle_sync_aggregate_results(self, results: list, usage_id: int):
        try:
            result = aggregate_translation_results(results, usage_id)
            return self.construct_http_response(result)
        except Exception as e:
            return self.handle_sync_error(e)

    def handle_sync_error(self, exception):
        """
        Handle errors during synchronous translation processing.
        """
        logger.error(f"Synchronous processing failed: {exception}", exc_info=True)
        response_data = {"error": str(exception)}
        if settings.DEBUG:
            response_data["stack_trace"] = traceback.format_exc()
        return Response(response_data, status=500)

    def construct_http_response(self, result: dict):
        """
        Constructs an HttpResponse based on the task result.
        """
        content = result.get("result", "")
        content_type = result.get("content_type", "application/json")
        filename = result.get("filename", "result")
        response = HttpResponse(content, content_type=content_type)
        if filename:
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class CombinedTranslateFileAPIView(CombinedBaseTranslationAPIView):
    """
    Translate a file (txt/PageXML) with optional pipeline processing.
    Supports both sync and async processing.
    """
    parser_classes = [MultiPartParser]
    serializer_class = CombinedTranslateFileSerializer

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        api_key = self.get_api_key(request)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        _file = serializer.validated_data.get("file")
        source = serializer.validated_data.get("source")
        target = serializer.validated_data.get("target")
        options = serializer.validated_data.get("options", [])
        async_param = serializer.validated_data.get("async_param", False)

        file_content = _file.read()
        file_name = _file.name

        # Retrieve and validate pipeline steps
        steps, render_txt, steps_keys = self.get_pipeline_steps(options)

        # Create usage record
        usage = UsageTranslationFile.objects.create(
            api_key=api_key,
            status=StatusField.IN_PROGRESS,
            source_language=source,
            target_language=target,
            source_size=_file.size,
        )

        if async_param:
            return self.handle_async_translate(
                usage_id=usage.id,
                file_content=file_content,
                source=source,
                target=target,
                file_name=file_name,
                steps_keys=steps_keys,
                render_txt=render_txt
            )

        # Synchronous processing
        return self.handle_sync_translate(
            usage_id=usage.id,
            file_content=file_content,
            source=source,
            target=target,
            file_name=file_name,
            steps_keys=steps_keys,
            render_txt=render_txt
        )


class CombinedTranslateSnippetAPIView(CombinedBaseTranslationAPIView):
    """
    Translate a text snippet with optional pipeline processing.
    Supports only synchronous processing.
    """
    parser_classes = [MultiPartParser]
    serializer_class = CombinedTranslateSnippetSerializer

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        api_key = self.get_api_key(request)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        snippet = serializer.validated_data.get("snippet")
        source = serializer.validated_data.get("source")
        target = serializer.validated_data.get("target")
        options = serializer.validated_data.get("options", [])

        # Retrieve and validate pipeline steps
        steps, render_txt, steps_keys = self.get_pipeline_steps(options)

        # Create usage record
        usage = UsageTranslationSnippet.objects.create(
            api_key=api_key,
            status=StatusField.IN_PROGRESS,
            source_language=source,
            target_language=target,
            source_size=len(snippet),
        )

        # Synchronous processing
        try:
            if steps_keys:
                # Use pipeline task
                result = translate_pipeline_task(snippet.encode('utf-8'), source, target, steps_keys, render_txt)
                translation = result.get('result', '')
            else:
                # Use simple connector
                connector = CEFETranslationConnector()
                translation = connector.translate_snippet(snippet, source, target)
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            usage.status = StatusField.FAILED
            usage.save()
            return Response({"error": "Translation failed"}, status=500)

        usage.target_size = len(translation)
        usage.status = StatusField.SUCCESS
        usage.save()

        return Response({"translation": translation})


class CombinedTranslatePipelineBatchAPIView(CombinedBaseTranslationAPIView):
    """
    Translate multiple files contained in a ZIP file with optional pipeline processing.
    Supports both sync and async processing.
    """
    parser_classes = [MultiPartParser]
    serializer_class = CombinedTranslateBatchSerializer

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        api_key = self.get_api_key(request)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("Invalid serializer data", extra={'data': serializer.errors})
            return Response(serializer.errors, status=400)

        zip_file = serializer.validated_data.get("file")
        source_lang = serializer.validated_data.get("source")
        target_lang = serializer.validated_data.get("target")
        options = serializer.validated_data.get("options", [])
        async_param = serializer.validated_data.get("async_param", False)

        zip_content = zip_file.read()

        usage = UsageTranslationFile.objects.create(
            api_key=api_key,
            status=StatusField.IN_PROGRESS,
            source_language=source_lang,
            target_language=target_lang,
            source_size=zip_file.size,
        )

        steps, render_txt, steps_keys = self.get_pipeline_steps(options)

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                input_dir = os.path.join(temp_dir, "input")
                os.makedirs(input_dir, exist_ok=True)

                # Save zip content to a temporary file
                zip_path = os.path.join(temp_dir, "files.zip")
                with open(zip_path, "wb") as f:
                    f.write(zip_content)
                logger.debug(f"Saved zip content to {zip_path} for usage_id={usage.id}")

                # Securely extract zip files
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    for member in zip_ref.namelist():
                        member_path = os.path.join(input_dir, member)
                        if not os.path.abspath(member_path).startswith(os.path.abspath(input_dir)):
                            logger.error(
                                f"Attempted Zip Slip attack detected with file: {member} for usage_id={usage.id}")
                            return Response({"error": f"Unsafe file path in zip: {member}"}, status=400)
                    zip_ref.extractall(input_dir)
                logger.info(f"Extracted zip content to {input_dir} for usage_id={usage.id}")

                filenames = os.listdir(input_dir)
                if not filenames:
                    logger.error(f"No files found in the zip archive for usage_id={usage.id}")
                    return Response({"error": "No files found in the uploaded zip archive."}, status=400)

                tasks = []
                for basename in filenames:
                    file_path = os.path.join(input_dir, basename)
                    with open(file_path, "rb") as f:
                        file_content = f.read()

                    if async_param:
                        task = translate_pipeline_task.s(
                            file_content, source_lang, target_lang, steps_keys, render_txt
                        )
                        tasks.append(task)
                        logger.debug(f"Created translate_pipeline_task for file: {basename} for usage_id={usage.id}")
                    else:
                        try:
                            result = translate_pipeline_task(file_content, source_lang, target_lang, steps_keys,
                                                             render_txt)
                            tasks.append(result)
                        except Exception as e:
                            return self.handle_sync_error(e)

                if not tasks:
                    logger.error(f"No valid tasks created from the zip archive for usage_id={usage.id}")
                    return Response({"error": "No valid tasks created from the zip archive."}, status=400)

                if async_param:
                    return self.handle_async_aggregate_results(tasks, usage.id)
                else:
                    return self.handle_sync_aggregate_results(tasks, usage.id)

        except zipfile.BadZipFile:
            logger.error(f"Invalid zip file provided for usage_id={usage.id}")
            return Response({"error": "Invalid zip file provided."}, status=400)
        except Exception as e:
            logger.error(f"Batch translation process failed for usage_id={usage.id}: {e}", exc_info=True)
            return Response({"error": "Batch translation process failed."}, status=500)


class TranslateSnippetAPIView(BaseTranslationAPIView):
    """
    Translate a text snippet from source language to target language.
    """

    parser_classes = [MultiPartParser]
    serializer_class = TranslateSnippetSerializer

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        api_key = self.get_api_key(request)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        snippet = serializer.validated_data.get("snippet")
        source = serializer.validated_data.get("source")
        target = serializer.validated_data.get("target")

        connector = CEFETranslationConnector()

        usage = UsageTranslationSnippet.objects.create(
            api_key=api_key,
            status=StatusField.IN_PROGRESS,
            source_language=source,
            target_language=target,
            source_size=len(snippet),
        )

        try:
            translation = connector.translate_snippet(snippet, source, target)
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            usage.set_status(StatusField.FAILED)
            return Response({"error": "Translation failed"}, status=500)

        usage.target_size = len(translation)
        usage.status = StatusField.SUCCESS
        usage.save()

        return Response({"translation": translation})


class TranslateFileAPIView(BaseTranslationAPIView):
    """
    Translate the content of an uploaded file from source language to target language.
    """

    parser_classes = [MultiPartParser]
    serializer_class = TranslateFileSerializer

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        api_key = self.get_api_key(request)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        _file = serializer.validated_data.get("file")
        source = serializer.validated_data.get("source")
        target = serializer.validated_data.get("target")

        file_content = _file.read()
        file_name = _file.name  # Get the file name if available

        usage = UsageTranslationFile.objects.create(
            api_key=api_key,
            status=StatusField.IN_PROGRESS,
            source_language=source,
            target_language=target,
            source_size=_file.size,
        )

        # Enqueue the translation task
        task = translate_file_task.apply_async(
            args=[usage.id, file_content, source, target, file_name]
        )

        return Response({"task_id": task.id, "status": "Processing"}, status=202)


class TranslatePipelineAPIView(BaseTranslationAPIView):
    """
    Submit a file to be translated using a specified pipeline.
    The pipeline can process text files or PageXML files according to the specified steps.
    """

    parser_classes = [MultiPartParser]
    serializer_class = TranslatePipelineSerializer

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        api_key = self.get_api_key(request)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        file = serializer.validated_data["file"]
        file_content = file.read()

        source_lang = serializer.validated_data["source"]
        target_lang = serializer.validated_data["target"]
        options = serializer.validated_data.get("options")

        steps, render_txt, steps_keys = self.get_pipeline_steps(options)

        usage = UsageTranslationFile.objects.create(
            api_key=api_key,
            source_language=source_lang,
            target_language=target_lang,
            source_size=file.size
        )

        # Enqueue the translation pipeline task
        task = translate_pipeline_task.apply_async(
            args=[file_content, source_lang, target_lang, steps_keys, render_txt]
        )

        return Response({"task_id": task.id, "status": "Processing"}, status=202)


class TranslatePipelineBatchAPIView(BaseTranslationAPIView):
    """
    Submit a ZIP file containing multiple files to be translated in batch using a specified pipeline.
    """

    parser_classes = [MultiPartParser]
    serializer_class = TranslatePipelineSerializer

    @handle_exceptions
    def post(self, request, *args, **kwargs):
        api_key = self.get_api_key(request)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("Invalid serializer data", extra={'data': serializer.errors})
            return Response(serializer.errors, status=400)

        zip_file = serializer.validated_data.get("file")
        zip_content = zip_file.read()

        source_lang = serializer.validated_data["source"]
        target_lang = serializer.validated_data["target"]
        options = serializer.validated_data.get("options")

        steps, render_txt, steps_keys = self.get_pipeline_steps(options)

        # Create the usage record first
        usage = UsageTranslationFile.objects.create(
            api_key=api_key,
            source_language=source_lang,
            target_language=target_lang,
            source_size=zip_file.size,
            status=StatusField.IN_PROGRESS
        )

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                input_dir = os.path.join(temp_dir, "input")
                os.makedirs(input_dir, exist_ok=True)

                # Save zip content to a temporary file
                zip_path = os.path.join(temp_dir, "files.zip")
                with open(zip_path, "wb") as f:
                    f.write(zip_content)
                logger.debug(f"Saved zip content to {zip_path} for usage_id={usage.id}")

                # Securely extract zip files
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    for member in zip_ref.namelist():
                        member_path = os.path.join(input_dir, member)
                        if not os.path.abspath(member_path).startswith(os.path.abspath(input_dir)):
                            logger.error(
                                f"Attempted Zip Slip attack detected with file: {member} for usage_id={usage.id}")
                            return Response({"error": f"Unsafe file path in zip: {member}"}, status=400)
                    zip_ref.extractall(input_dir)
                logger.info(f"Extracted zip content to {input_dir} for usage_id={usage.id}")

                filenames = os.listdir(input_dir)
                if not filenames:
                    logger.error(f"No files found in the zip archive for usage_id={usage.id}")
                    return Response({"error": "No files found in the uploaded zip archive."}, status=400)

                tasks = []
                for basename in filenames:
                    file_path = os.path.join(input_dir, basename)
                    with open(file_path, "rb") as f:
                        file_content = f.read()

                    task = translate_pipeline_task.s(
                        file_content=file_content,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        steps_keys=steps_keys,
                        render_txt=render_txt
                    )
                    tasks.append(task)
                    logger.debug(f"Created translate_pipeline_task for file: {basename} for usage_id={usage.id}")

                if not tasks:
                    logger.error(f"No valid tasks created from the zip archive for usage_id={usage.id}")
                    return Response({"error": "No valid tasks created from the zip archive."}, status=400)

                # Define the callback task with usage_id
                callback_task = aggregate_translation_results.s(usage_id=usage.id)

                # Create a chord and apply it
                chord_result = chord(tasks)(callback_task)
                logger.info(f"Chord initiated with callback task ID: {chord_result.id} for usage_id={usage.id}")

                # Return the callback_task.id (which is chord_result.id) to the user
                return Response({"task_id": chord_result.id, "status": "Processing"}, status=202)

        except zipfile.BadZipFile:
            logger.error(f"Invalid zip file provided for usage_id={usage.id}")
            return Response({"error": "Invalid zip file provided."}, status=400)
        except Exception as e:
            logger.error(f"Batch translation process failed for usage_id={usage.id}: {e}", exc_info=True)
            return Response({"error": "Batch translation process failed."}, status=500)


class TranslatePipelineOptionsAPIView(APIView):
    """
    Retrieve available pipeline options for translation.
    """

    permission_classes = [HasOrganisationAPIKey]

    @extend_schema(
        description="Retrieve available pipeline options for translation.",
        responses={
            200: OpenApiResponse(description="List of available pipeline options"),
        },
    )
    def get(self, request, *args, **kwargs):
        step_representation = PipelineStepEnum.get_representation()
        return Response(step_representation)


class TranslationJobStatusAPIView(APIView):
    """
    Check the status of a translation job using its task ID.
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
            return Response({"status": task_result.state}, status=200)


class TranslationJobResultAPIView(APIView):
    """
    Retrieve the result of a completed translation job using its task ID.
    """

    permission_classes = [HasOrganisationAPIKey]

    def get(self, request, task_id, *args, **kwargs):
        task_result = AsyncResult(task_id)
        if task_result.state == 'PENDING':
            return Response({"status": "Pending"}, status=200)
        elif task_result.state == 'SUCCESS':
            result_data = task_result.result
            logger.debug(f"Task result type: {type(result_data)}")
            logger.debug(f"Task result content: {result_data}")

            if isinstance(result_data, dict):
                result = result_data.get('result')
                content_type = result_data.get('content_type', 'application/json')
                response = HttpResponse(result, content_type=content_type)
                # Handle filename for attachments (e.g., zip files)
                if 'filename' in result_data:
                    filename = result_data['filename']
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            elif isinstance(result_data, bytes):
                # Handle bytes directly
                return HttpResponse(result_data, content_type='application/octet-stream')
            else:
                # Handle other cases if necessary
                return HttpResponse(result_data, content_type='text/plain')
        elif task_result.state == 'FAILURE':
            error_message = str(task_result.result)
            return Response({"status": "Failed", "error": error_message}, status=500)
        else:
            return Response({"status": task_result.state}, status=200)
