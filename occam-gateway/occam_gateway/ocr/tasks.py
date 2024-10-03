import logging
import os
import traceback
from io import BytesIO
from tempfile import NamedTemporaryFile

import pdf2image
import requests
from billiard.exceptions import SoftTimeLimitExceeded
from celery import shared_task

from shared.pipeline import PageXMLWrapper, ocr_pipeline, PipelineStepEnum
from .models import OCREngine
from .ocr_engine_mapping import get_connector_for_engine
from .ocr_postprocess_xml import add_custom_reading_order

logger = logging.getLogger("django")

TIME_LIMIT = 1200  # in seconds


@shared_task(
    bind=True,
    queue='ocr_queue',
    time_limit=TIME_LIMIT,
    soft_time_limit=TIME_LIMIT - 10
)
def process_ocr_image_task(self, file_content: bytes, engine_id: int) -> dict:
    """
    Celery task to process OCR on image files.
    """
    try:
        logger.info(f"Starting OCR image task for engine_id={engine_id}")
        engine = OCREngine.objects.get(pk=engine_id)
        connector = get_connector_for_engine(engine)

        data = connector.ocr_image(BytesIO(file_content))
        xml = add_custom_reading_order(data.get("xml"))

        if not xml:
            error_msg = "OCR failed: No XML found"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"OCR image task completed successfully for engine_id={engine_id}")
        return {'result': xml, 'content_type': 'application/xml'}

    except OCREngine.DoesNotExist:
        error_msg = f"OCREngine with id={engine_id} does not exist."
        logger.error(error_msg)
        raise ValueError(error_msg)

    except SoftTimeLimitExceeded:
        error_msg = f"OCR image task hit soft time limit for engine_id={engine_id}"
        logger.error(error_msg)
        raise

    except Exception as e:
        logger.error(f"OCR image task failed for engine_id={engine_id}: {e}", exc_info=True)
        raise


@shared_task(
    bind=True,
    queue='ocr_queue',
    time_limit=TIME_LIMIT,
    soft_time_limit=TIME_LIMIT - 10
)
def process_ocr_url_task(self, image_url: str, engine_id: int) -> dict:
    """
    Celery task to process OCR on images fetched from URLs.
    """
    try:
        logger.info(f"Starting OCR URL task for image_url={image_url}, engine_id={engine_id}")
        engine = OCREngine.objects.get(pk=engine_id)
        connector = get_connector_for_engine(engine)

        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            error_msg = f"URL does not point to an image. Content-Type: {content_type}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        image_content = response.content

        data = connector.ocr_image(BytesIO(image_content))
        xml = add_custom_reading_order(data.get("xml"))

        if not xml:
            error_msg = "OCR failed: No XML found"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"OCR URL task completed successfully for image_url={image_url}, engine_id={engine_id}")
        return {'result': xml, 'content_type': 'application/xml'}

    except OCREngine.DoesNotExist:
        error_msg = f"OCREngine with id={engine_id} does not exist."
        logger.error(error_msg)
        raise ValueError(error_msg)

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request failed for image_url={image_url}, engine_id={engine_id}: {e}", exc_info=True)
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            error_msg = f"Max retries exceeded for image_url={image_url}, engine_id={engine_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    except SoftTimeLimitExceeded:
        error_msg = f"OCR URL task hit soft time limit for image_url={image_url}, engine_id={engine_id}"
        logger.error(error_msg)
        raise

    except Exception as e:
        logger.error(f"OCR URL task failed for image_url={image_url}, engine_id={engine_id}: {e}", exc_info=True)
        raise


@shared_task(
    bind=True,
    queue='ocr_queue',
    time_limit=TIME_LIMIT,
    soft_time_limit=TIME_LIMIT - 10
)
def process_ocr_pdf_task(self, file_content: bytes, engine_id: int) -> dict:
    """
    Celery task to process OCR on PDF files by converting them to images first.
    """
    temp_file_path = None
    try:
        logger.info(f"Starting OCR PDF task for engine_id={engine_id}")
        engine = OCREngine.objects.get(pk=engine_id)
        connector = get_connector_for_engine(engine)

        with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        logger.debug(f"Saved temporary PDF file at {temp_file_path} for engine_id={engine_id}")

        try:
            images = pdf2image.convert_from_path(temp_file_path, fmt="png", dpi=300)
            logger.info(f"Converted PDF to {len(images)} images for OCR")
        except Exception as e:
            logger.error(f"Failed to convert PDF to images for engine_id={engine_id}: {e}", exc_info=True)
            raise ValueError(f"Failed to convert PDF to images: {e}") from e

        xml_list = []
        for i, image in enumerate(images, start=1):
            try:
                image_io = BytesIO()
                image.save(image_io, format="PNG")
                image_io.seek(0)
                data = connector.ocr_image(image_io)
                xml = add_custom_reading_order(data.get("xml"))
                if not xml:
                    error_msg = f"OCR failed on page {i}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                xml_list.append(xml)
                logger.debug(f"OCR successful for page {i}")
            except Exception as e:
                logger.error(f"OCR failed for page {i + 1} in PDF for engine_id={engine_id}: {e}", exc_info=True)
                raise

        # Combine XMLs as needed
        combined_xml = "\n".join(xml_list)
        logger.info(f"OCR PDF task completed successfully for engine_id={engine_id}")
        return {'result': combined_xml, 'content_type': 'application/xml'}

    except OCREngine.DoesNotExist:
        error_msg = f"OCREngine with id={engine_id} does not exist."
        logger.error(error_msg)
        raise ValueError(error_msg)

    except SoftTimeLimitExceeded:
        error_msg = f"OCR PDF task hit soft time limit for engine_id={engine_id}"
        logger.error(error_msg)
        raise

    except Exception as e:
        logger.error(f"OCR PDF task failed for engine_id={engine_id}: {e}", exc_info=True)
        raise
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.debug(f"Deleted temporary PDF file at {temp_file_path}")
            except Exception as cleanup_error:
                logger.error(f"Failed to delete temporary PDF file at {temp_file_path}: {cleanup_error}", exc_info=True)


@shared_task(
    bind=True,
    queue='ocr_queue',
    time_limit=TIME_LIMIT,
    soft_time_limit=TIME_LIMIT - 10
)
def process_ocr_pipeline_task(
    self,
    content,
    engine_id: int,
    steps_keys: list,
    source_lang: str,
    render_txt: bool,
    content_type: str  # New parameter to handle 'file' or 'url'
) -> dict:
    """
    Celery task to process OCR with additional pipeline steps for post-processing.
    Handles both file content and URLs based on content_type.
    """
    try:
        logger.info(
            f"Starting OCR pipeline task for engine_id={engine_id}, source_lang={source_lang}, "
            f"render_txt={render_txt}, content_type={content_type}, steps_keys={steps_keys}"
        )
        engine = OCREngine.objects.get(pk=engine_id)
        connector = get_connector_for_engine(engine)

        # Handle content based on content_type
        if content_type == 'url':
            image_url = content
            logger.info(f"Fetching image from URL: {image_url}")
            try:
                response = requests.get(image_url, timeout=30)
                response.raise_for_status()
                fetched_content_type = response.headers.get("Content-Type", "")
                if not fetched_content_type.startswith("image/"):
                    error_msg = f"URL does not point to an image. Content-Type: {fetched_content_type}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                file_content = response.content
                logger.debug(f"Fetched image from URL: {image_url} (size: {len(file_content)} bytes)")
            except requests.RequestException as e:
                logger.error(f"Failed to fetch image from URL: {e}")
                raise ValueError(f"Failed to fetch image from URL: {e}") from e
            file_bytes = BytesIO(file_content)
        elif content_type in ['image', 'pdf']:
            file_bytes = BytesIO(content)
        else:
            error_msg = f"Unsupported content_type: {content_type}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Perform OCR
        data = connector.ocr_image(file_bytes)
        xml = add_custom_reading_order(data.get("xml"))

        if not xml:
            error_msg = "OCR failed: No XML found"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Convert step keys to step classes, filtering out invalid steps
        steps = []
        for key in steps_keys:
            step = PipelineStepEnum.get_by_key(key)
            if not step:
                logger.warning(f"Invalid pipeline step key: {key}")
                continue
            steps.append(step)

        if not steps:
            error_msg = "No valid pipeline steps provided."
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Run the pipeline
        page_xml = PageXMLWrapper()
        page_xml.parse(BytesIO(xml.encode('utf-8')))
        page_xml_trans = ocr_pipeline(
            page_xml, source_lang=source_lang, steps=steps, reconstruct=not render_txt
        )

        result = str(page_xml_trans)
        if not render_txt:
            result_content_type = "application/xml"
        else:
            result_content_type = "text/plain"

        logger.info(f"OCR pipeline task completed successfully for engine_id={engine_id}")
        return {'result': result, 'content_type': result_content_type}

    except OCREngine.DoesNotExist:
        error_msg = f"OCREngine with id={engine_id} does not exist."
        logger.error(error_msg)
        raise ValueError(error_msg)

    except SoftTimeLimitExceeded:
        error_msg = f"OCR pipeline task hit soft time limit for engine_id={engine_id}"
        logger.error(error_msg)
        raise
    except Exception as e:
        tb = traceback.format_exc()
        error_message = f"OCR pipeline task failed for engine_id={engine_id}: {str(e)}\n{tb}"
        logger.error(error_message)
        raise Exception("An error occurred during OCR processing. Please try again later.")
