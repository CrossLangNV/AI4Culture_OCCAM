# translation/tasks.py
import io
import logging
import os
import tempfile
import zipfile

import chardet
from billiard.exceptions import SoftTimeLimitExceeded
from celery import shared_task
from lxml import etree

from shared.pipeline import translate_pipeline, PageXMLWrapper, PipelineStepEnum
from .connector import CEFETranslationConnector

logger = logging.getLogger("django")

TIME_LIMIT = 1200  # in seconds


@shared_task(
    bind=True,
    queue='translation_queue',
    time_limit=TIME_LIMIT,
    soft_time_limit=TIME_LIMIT - 10
)
def translate_file_task(self, usage_id: int, file_content: bytes, source_lang: str, target_lang: str,
                        file_name: str) -> dict:
    try:
        if isinstance(file_content, str):
            file_content = file_content.encode()
        logger.info(
            f"Task ID={self.request.id}: Starting translation for usage_id={usage_id}, file={file_name}, "
            f"source_lang={source_lang}, target_lang={target_lang}"
        )
        connector = CEFETranslationConnector()
        logger.debug(f"Task ID={self.request.id}: Initialized CEFETranslationConnector")

        with io.BytesIO(file_content) as file_obj:
            extension = os.path.splitext(file_name)[1].lower()
            content_type = {
                '.txt': 'text/plain',
                '.pdf': 'application/pdf',
                '.xml': 'application/xml'
            }.get(extension, 'application/octet-stream')
            logger.debug(f"Task ID={self.request.id}: File extension={extension}, content_type={content_type}")
            logger.debug(f"Task ID={self.request.id}: File size={len(file_content)} bytes")

            translation = connector.translate_file((file_name, file_obj, content_type), source_lang, target_lang)
            logger.debug(f"Task ID={self.request.id}: Translation connector returned successfully")

        logger.info(f"Task ID={self.request.id}: Translation successful for usage_id={usage_id}, file={file_name}")
        return {'result': translation, 'content_type': content_type, 'filename': file_name}
    except SoftTimeLimitExceeded:
        logger.error(
            f"Task ID={self.request.id}: Translation file task hit soft time limit for usage_id={usage_id}, file={file_name}"
        )
        raise
    except Exception as e:
        logger.error(
            f"Task ID={self.request.id}: Translation file task failed for usage_id={usage_id}, file={file_name}: {e}",
            exc_info=True
        )
        raise


@shared_task(
    bind=True,
    queue='translation_queue',
    time_limit=TIME_LIMIT,
    soft_time_limit=TIME_LIMIT - 10
)
def translate_pipeline_task(self, file_content: bytes, source_lang: str,
                            target_lang: str, steps_keys: list, render_txt: bool) -> dict:
    try:
        if isinstance(file_content, str):
            file_content = file_content.encode()

        logger.info(f"Task ID={self.request.id}: Starting pipeline translation task")
        logger.debug(
            f"Task ID={self.request.id}: Parameters - source_lang={source_lang}, target_lang={target_lang}, "
            f"steps_keys={steps_keys}, render_txt={render_txt}"
        )

        # Determine if the file is XML
        is_xml = False
        logger.debug(f"Task ID={self.request.id}: Attempting to parse file content as XML")
        try:
            etree.parse(io.BytesIO(file_content))
            is_xml = True
            logger.debug(f"Task ID={self.request.id}: Successfully parsed file content as XML")
        except etree.XMLSyntaxError:
            logger.debug(f"Task ID={self.request.id}: XML parsing failed, treating as non-XML")

        if is_xml:
            page_xml = PageXMLWrapper()
            page_xml.parse(io.BytesIO(file_content))
            logger.debug(f"Task ID={self.request.id}: Parsed XML content into PageXMLWrapper")
        else:
            detection = chardet.detect(file_content)
            logger.debug(f"Task ID={self.request.id}: Encoding detection result: {detection}")
            encoding = detection.get('encoding')
            confidence = detection.get('confidence', 0)
            logger.info(
                f"Task ID={self.request.id}: Detected encoding: {encoding} with confidence {confidence}"
            )

            if not encoding or confidence < 0.5:
                error_msg = "Unable to reliably detect file encoding."
                logger.error(f"Task ID={self.request.id}: {error_msg}")
                raise ValueError(error_msg)

            try:
                decoded_content = file_content.decode(encoding)
                page_xml = decoded_content
                logger.info(f"Task ID={self.request.id}: Successfully decoded content using {encoding}")
            except UnicodeDecodeError as e:
                logger.error(
                    f"Task ID={self.request.id}: Decoding failed with encoding {encoding}: {e}"
                )
                raise ValueError(f"Decoding failed: {e}") from e

        # Convert step keys to step classes, filtering out invalid steps
        steps = []
        for key in steps_keys:
            step = PipelineStepEnum.get_by_key(key)
            if not step:
                logger.warning(f"Task ID={self.request.id}: Invalid pipeline step key: {key}")
                continue
            steps.append(step)

        if not steps:
            error_msg = "No valid pipeline steps provided."
            logger.error(f"Task ID={self.request.id}: {error_msg}")
            raise ValueError(error_msg)
        logger.debug(
            f"Task ID={self.request.id}: Applying pipeline steps: {[step for step in steps]}"
        )

        # Run the translation pipeline
        page_xml_trans = translate_pipeline(
            page_xml,
            source_lang=source_lang,
            target_lang=target_lang,
            steps=steps,
            reconstruct=not render_txt,
        )
        logger.debug(
            f"Task ID={self.request.id}: Pipeline translation completed with result type {type(page_xml_trans)}")

        if isinstance(page_xml_trans, list):
            result = "\n\n".join("\n".join(paragraph) for paragraph in page_xml_trans)
            logger.debug(f"Task ID={self.request.id}: Formatted translation result as concatenated string")
        else:
            result = str(page_xml_trans)
            logger.debug(f"Task ID={self.request.id}: Converted translation result to string")

        content_type = "application/xml" if is_xml and not render_txt else "text/plain"
        extension = '.xml' if content_type == 'application/xml' else '.txt'
        filename = f"translated_{self.request.id}{extension}"
        logger.debug(f"Task ID={self.request.id}: Set content_type={content_type}, filename={filename}")

        logger.info(f"Task ID={self.request.id}: Pipeline translation successful")
        return {'result': result, 'content_type': content_type, 'filename': filename}
    except SoftTimeLimitExceeded:
        logger.error(f"Task ID={self.request.id}: Translation pipeline task hit soft time limit")
        raise
    except Exception as e:
        logger.error(
            f"Task ID={self.request.id}: Translation pipeline task failed: {e}",
            exc_info=True
        )
        raise


@shared_task(
    bind=True,
    queue='translation_queue',
    time_limit=TIME_LIMIT,
    soft_time_limit=TIME_LIMIT - 10
)
def aggregate_translation_results(self, results: list, usage_id: int) -> dict:
    try:
        logger.debug(f"Task ID={self.request.id}: Aggregating {len(results)} results for usage_id={usage_id}")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = os.path.join(temp_dir, "output")
            os.makedirs(output_dir, exist_ok=True)
            logger.debug(f"Task ID={self.request.id}: Created temporary output directory at {output_dir}")

            for idx, result in enumerate(results, start=1):
                filename = result.get('filename', f'result_{idx}')
                content = result['result']
                content_type = result.get('content_type', 'text/plain')

                # Sanitize filename to prevent directory traversal
                filename = os.path.basename(filename)

                # Ensure the correct file extension is used
                if content_type == 'application/xml' and not filename.endswith('.xml'):
                    filename += '.xml'
                elif content_type == 'text/plain' and not filename.endswith('.txt'):
                    filename += '.txt'

                output_file_path = os.path.join(output_dir, filename)
                logger.debug(
                    f"Task ID={self.request.id}: Writing result {idx} to {output_file_path} with content_type={content_type}"
                )

                # Handle the content, joining it if necessary
                if isinstance(content, list):
                    content = "\n\n".join(content)
                    logger.debug(f"Task ID={self.request.id}: Joined list content into string for file {filename}")

                with open(output_file_path, "w", encoding='utf-8') as out_f:
                    out_f.write(content)
                    logger.debug(f"Task ID={self.request.id}: Written content to {output_file_path}")

            zip_output_path = os.path.join(temp_dir, "output.zip")
            logger.debug(f"Task ID={self.request.id}: Creating zip archive at {zip_output_path}")

            with zipfile.ZipFile(zip_output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for basename in os.listdir(output_dir):
                    file_path = os.path.join(output_dir, basename)
                    zf.write(file_path, basename)
                    logger.debug(f"Task ID={self.request.id}: Added {basename} to zip archive")

            with open(zip_output_path, "rb") as zf:
                zip_content = zf.read()
                logger.debug(f"Task ID={self.request.id}: Read zip archive content, size={len(zip_content)} bytes")

        # Update the task's result in Celery's result backend
        logger.info(
            f"Task ID={self.request.id}: Aggregation successful for usage_id={usage_id}, zip size={len(zip_content)} bytes"
        )
        return {'result': zip_content, 'content_type': 'application/zip', 'filename': 'output.zip'}

    except SoftTimeLimitExceeded:
        logger.error(f"Task ID={self.request.id}: Aggregation task hit soft time limit for usage_id={usage_id}")
        raise
    except Exception as e:
        logger.error(
            f"Task ID={self.request.id}: Aggregation failed for usage_id={usage_id}: {e}",
            exc_info=True
        )
        raise
