import logging
import os
import traceback
from io import BytesIO
from tempfile import NamedTemporaryFile
import json
import re

import pdf2image
import requests
from billiard.exceptions import SoftTimeLimitExceeded
from celery import shared_task

from shared.pipeline import PageXMLWrapper, ocr_pipeline, PipelineStepEnum
from ocr.models import OCREngine
from ocr.ocr_engine_mapping import get_connector_for_engine
from ocr.ocr_postprocess_xml import add_custom_reading_order
from ocr.pagexml2geojson import main_from_xml_string

logger = logging.getLogger("django")

TIME_LIMIT = 1200  # in seconds

def _split_into_sentences(text):
    sentence_endings = re.compile(r'(?<=[.!?])\s+')
    sentences = sentence_endings.split(text.strip())
    return sentences

def _xml2sentences(xml_str: str) -> str:
    """
    Convert xml string to sentences by extracting text and splitting into sentences.
    We'll do something similar to the original logic:
    1. Extract all text (itertext) since we don't have a strict <p> structure.
    2. Split into sentences.
    """
    try:
        from lxml import etree
        parser = etree.XMLParser(recover=True)
        root = etree.fromstring(xml_str.encode('utf-8'), parser=parser)
        # Extract all text from the XML
        full_text = ''.join(root.itertext())
        # Split into sentences
        sentences = _split_into_sentences(full_text)
        return "\n".join(sentences)
    except Exception as e:
        logger.error(f"XML parsing or sentence segmentation error: {e}", exc_info=True)
        # If error, just return the full text without sentence splitting
        return ''.join(root.itertext()) if 'root' in locals() else xml_str


@shared_task(
    bind=True,
    queue='ocr_queue',
    time_limit=TIME_LIMIT,
    soft_time_limit=TIME_LIMIT - 10
)
def process_ocr_image_task(self, file_content: bytes, engine_id: int) -> dict:
    """
    Celery task to process OCR on image files.
    Returns JSON with {text, geojson, pagexml}.
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

        # Produce geojson and text from xml
        geojson = main_from_xml_string(xml)
        sentences = _xml2sentences(xml)

        # Prepare JSON result
        result_dict = {
            "text": sentences,
            "geojson": geojson,
            "pagexml": xml
        }
        result_json = json.dumps(result_dict)
        logger.info(f"OCR image task completed successfully for engine_id={engine_id}")
        return {'result': result_json, 'content_type': 'application/json'}

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
    Now returns JSON with text, geojson, pagexml.
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

        geojson = main_from_xml_string(xml)
        sentences = _xml2sentences(xml)

        result_dict = {
            "text": sentences,
            "geojson": geojson,
            "pagexml": xml
        }
        result_json = json.dumps(result_dict)
        logger.info(f"OCR URL task completed successfully for image_url={image_url}, engine_id={engine_id}")
        return {'result': result_json, 'content_type': 'application/json'}

    except OCREngine.DoesNotExist:
        error_msg = f"OCREngine with id={engine_id} does not exist."
        logger.error(error_msg)
        raise ValueError(error_msg)
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request failed for image_url={image_url}: {e}", exc_info=True)
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
    Celery task to process OCR on PDF files.
    Returns JSON with text, geojson (merged?), and combined pagexml.
    """
    temp_file_path = None
    try:
        logger.info(f"Starting OCR PDF task for engine_id={engine_id}")
        engine = OCREngine.objects.get(pk=engine_id)
        connector = get_connector_for_engine(engine)

        with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        images = pdf2image.convert_from_path(temp_file_path, fmt="png", dpi=300)
        logger.info(f"Converted PDF to {len(images)} images for OCR")

        xml_list = []
        for i, image in enumerate(images, start=1):
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

        combined_xml = "\n".join(xml_list)

        # Produce geojson and text from combined xml (just combine them)
        # This may not be perfect if multiple pages are concatenated.
        # A simple approach is to treat combined_xml as one big document:
        geojson = main_from_xml_string(combined_xml)
        sentences = _xml2sentences(combined_xml)

        result_dict = {
            "text": sentences,
            "geojson": geojson,
            "pagexml": combined_xml
        }
        result_json = json.dumps(result_dict)

        logger.info(f"OCR PDF task completed successfully for engine_id={engine_id}")
        return {'result': result_json, 'content_type': 'application/json'}

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
    content_type: str
) -> dict:
    """
    Celery task to process OCR with pipeline steps and return text, geojson, and pagexml as JSON.
    """
    try:
        logger.info(
            f"Starting OCR pipeline task for engine_id={engine_id}, source_lang={source_lang}, "
            f"render_txt={render_txt}, content_type={content_type}, steps_keys={steps_keys}"
        )
        engine = OCREngine.objects.get(pk=engine_id)
        connector = get_connector_for_engine(engine)

        if content_type == 'url':
            image_url = content
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            fetched_content_type = response.headers.get("Content-Type", "")
            if not fetched_content_type.startswith("image/"):
                error_msg = f"URL not image. Content-Type: {fetched_content_type}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            file_bytes = BytesIO(response.content)
        elif content_type in ['image', 'pdf']:
            file_bytes = BytesIO(content)
        else:
            error_msg = f"Unsupported content_type: {content_type}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        data = connector.ocr_image(file_bytes)
        xml = add_custom_reading_order(data.get("xml"))
        if not xml:
            error_msg = "OCR failed: No XML found"
            logger.error(error_msg)
            raise ValueError(error_msg)

        steps = []
        for key in steps_keys:
            step = PipelineStepEnum.get_by_key(key)
            if step:
                steps.append(step)

        if not steps:
            error_msg = "No valid pipeline steps provided."
            logger.error(error_msg)
            raise ValueError(error_msg)

        page_xml = PageXMLWrapper()
        page_xml.parse(BytesIO(xml.encode('utf-8')))
        page_xml_trans = ocr_pipeline(
            page_xml, source_lang=source_lang, steps=steps, reconstruct=not render_txt
        )

        result_str = str(page_xml_trans)

        # Produce geojson and text from final XML result
        # If render_txt is True, result_str will be plaintext?
        # If not render_txt, it's XML. Let's assume if it's XML, we can still parse geojson and sentences.
        final_xml = result_str if not render_txt else xml  # If we ended as text, fallback to original XML for geojson?
        if render_txt:
            # If render_txt is true, we have text only, no xml to parse for geojson.
            # Let's return geojson empty or from original xml?
            # We can decide to always return geojson from original xml:
            geojson = main_from_xml_string(xml)
            sentences = _xml2sentences(xml)
            # final pagexml: since we ended in text, pagexml in final result can be original xml
            pagexml_output = xml
            final_text = result_str
        else:
            # result_str is XML
            geojson = main_from_xml_string(result_str)
            sentences = _xml2sentences(result_str)
            pagexml_output = result_str
            final_text = sentences  # The pipeline might have changed text, but let's keep consistent

        result_dict = {
            "text": final_text,
            "geojson": geojson,
            "pagexml": pagexml_output
        }

        result_json = json.dumps(result_dict)
        logger.info(f"OCR pipeline task completed successfully for engine_id={engine_id}")
        return {'result': result_json, 'content_type': 'application/json'}

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
        raise Exception("An error occurred during OCR processing.") from e
