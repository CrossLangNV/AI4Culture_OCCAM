# correction/tasks.py

import logging
import os
import tempfile
from xml.etree.ElementTree import ParseError

from billiard.exceptions import SoftTimeLimitExceeded
from celery import shared_task
from lxml import etree

from ocr.pagexml2geojson import main_from_xml_string
from shared.models import StatusField
from shared.pipeline import PageXMLWrapper, PageXMLParagraphParser, TextParagraphParser
from .connector import CorrectionConnector
from .enums import CorrectionEnum
from .models import UsageCorrection
from .ocr_correction_manual import OCRCorrectorManual

TIME_LIMIT = 1200  # 20 minutes, for example
logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    queue='ocr_queue',  # or create a dedicated 'correction_queue' if you prefer
    time_limit=TIME_LIMIT,
    soft_time_limit=TIME_LIMIT - 10
)
def manual_correction_task(self, usage_id: int, ocr_content: bytes, transcription_content: bytes, params: dict) -> dict:
    """
    Asynchronous task to perform manual correction on two files (ocr + transcription).
    Returns a dict with the corrected XML.
    """
    try:
        usage = UsageCorrection.objects.get(id=usage_id)
        usage.set_status(StatusField.IN_PROGRESS)

        with tempfile.NamedTemporaryFile(delete=False) as temp_ocr_file, \
                tempfile.NamedTemporaryFile(delete=False) as temp_transcription_file, \
                tempfile.NamedTemporaryFile(delete=False) as temp_out_file:

            temp_ocr_file.write(ocr_content)
            temp_transcription_file.write(transcription_content)
            temp_ocr_file.close()
            temp_transcription_file.close()

            # We must ensure 'ocrfilename' and 'manfilename' are passed to OCRCorrectorManual
            corr_params = dict(params)  # copy so we don't mutate original
            corr_params['ocrfilename'] = temp_ocr_file.name
            corr_params['manfilename'] = temp_transcription_file.name

            ocr_corrector = OCRCorrectorManual(**corr_params)
            ocr_corrector.run(ocrupdatefile=temp_out_file.name)

            with open(temp_out_file.name, 'rb') as corrected_file:
                corrected_content = corrected_file.read()

        # Cleanup
        os.remove(temp_ocr_file.name)
        os.remove(temp_transcription_file.name)
        os.remove(temp_out_file.name)

        usage.set_status(StatusField.SUCCESS)
        usage.corrected_size = len(corrected_content)
        usage.save()

        return {
            'result': corrected_content.decode('utf-8'),
            'content_type': 'application/xml'
        }

    except UsageCorrection.DoesNotExist:
        logger.error(f"UsageCorrection with id={usage_id} does not exist.")
        raise ValueError(f"UsageCorrection with id={usage_id} does not exist.")
    except SoftTimeLimitExceeded:
        logger.error(f"manual_correction_task (usage_id={usage_id}) hit soft time limit.")
        raise
    except Exception as e:
        logger.error(
            f"Manual correction task failed (usage_id={usage_id}): {e}",
            exc_info=True
        )
        # If it fails, mark usage as failed
        try:
            usage.set_status(StatusField.FAILED)
        except:
            pass
        raise


@shared_task(
    bind=True,
    queue='ocr_queue',
    time_limit=TIME_LIMIT,
    soft_time_limit=TIME_LIMIT - 10
)
def manual_correction_string_task(self, usage_id: int, ocr_str: str, transcription_str: str, params: dict) -> dict:
    """
    Asynchronous task to perform manual correction on two strings (OCR + transcription).
    Returns a dict with the corrected XML.
    """
    try:
        usage = UsageCorrection.objects.get(id=usage_id)
        usage.set_status(StatusField.IN_PROGRESS)

        with tempfile.NamedTemporaryFile(delete=False) as temp_ocr_file, \
                tempfile.NamedTemporaryFile(delete=False) as temp_transcription_file, \
                tempfile.NamedTemporaryFile(delete=False) as temp_out_file:

            temp_ocr_file.write(ocr_str.encode("utf-8"))
            temp_transcription_file.write(transcription_str.encode("utf-8"))
            temp_ocr_file.close()
            temp_transcription_file.close()

            corr_params = dict(params)
            corr_params['ocrfilename'] = temp_ocr_file.name
            corr_params['manfilename'] = temp_transcription_file.name

            ocr_corrector = OCRCorrectorManual(**corr_params)
            ocr_corrector.run(ocrupdatefile=temp_out_file.name)

            with open(temp_out_file.name, "rb") as corrected_file:
                corrected_content = corrected_file.read()

        # Cleanup
        os.remove(temp_ocr_file.name)
        os.remove(temp_transcription_file.name)
        os.remove(temp_out_file.name)

        usage.set_status(StatusField.SUCCESS)
        usage.corrected_size = len(corrected_content)
        usage.save()

        return {
            'result': corrected_content.decode('utf-8'),
            'content_type': 'application/xml'
        }

    except UsageCorrection.DoesNotExist:
        logger.error(f"UsageCorrection with id={usage_id} does not exist.")
        raise ValueError(f"UsageCorrection with id={usage_id} does not exist.")
    except SoftTimeLimitExceeded:
        logger.error(f"manual_correction_string_task (usage_id={usage_id}) time limit.")
        raise
    except ParseError as parse_err:
        logger.error(
            f"XML parse error (usage_id={usage_id}): {parse_err}",
            exc_info=True
        )
        try:
            usage.set_status(StatusField.FAILED)
        except:
            pass
        # Return a structured result or just re-raise
        raise
    except Exception as e:
        logger.error(
            f"Manual correction from string task failed (usage_id={usage_id}): {e}",
            exc_info=True
        )
        try:
            usage.set_status(StatusField.FAILED)
        except:
            pass
        raise


@shared_task(
    bind=True,
    queue='ocr_queue',
    time_limit=TIME_LIMIT,
    soft_time_limit=TIME_LIMIT - 10
)
def manual_correction_geojson_task(self, usage_id: int, ocr_content: bytes, transcription_content: bytes,
                                   params: dict) -> dict:
    """
    Asynchronous task to perform manual correction, then return text, geojson, and pagexml as JSON
    (mirroring the OCRManualCorrectionGeoJsonAPIView).
    """
    try:
        usage = UsageCorrection.objects.get(id=usage_id)
        usage.set_status(StatusField.IN_PROGRESS)

        with tempfile.NamedTemporaryFile(delete=False) as temp_ocr_file, \
                tempfile.NamedTemporaryFile(delete=False) as temp_transcription_file, \
                tempfile.NamedTemporaryFile(delete=False) as temp_out_file:

            temp_ocr_file.write(ocr_content)
            temp_transcription_file.write(transcription_content)
            temp_ocr_file.close()
            temp_transcription_file.close()

            # We must ensure 'ocrfilename' and 'manfilename' are in the params
            corr_params = dict(params)
            corr_params['ocrfilename'] = temp_ocr_file.name
            corr_params['manfilename'] = temp_transcription_file.name

            ocr_corrector = OCRCorrectorManual(**corr_params)
            ocr_corrector.run(ocrupdatefile=temp_out_file.name)

            with open(temp_out_file.name, 'rb') as corrected_file:
                corrected_xml = corrected_file.read()

        # Cleanup
        os.remove(temp_ocr_file.name)
        os.remove(temp_transcription_file.name)
        os.remove(temp_out_file.name)

        corrected_xml_str = corrected_xml.decode('utf-8')
        from ocr.pagexml2geojson import main_from_xml_string

        text_sentences = _xml2sentences_helper(corrected_xml_str)
        geojson = main_from_xml_string(corrected_xml_str)

        usage.set_status(StatusField.SUCCESS)
        usage.corrected_size = len(corrected_xml)
        usage.save()

        # Return as JSON with text, geojson, pagexml keys
        import json
        result_dict = {
            "text": text_sentences,
            "geojson": geojson,
            "pagexml": corrected_xml_str
        }
        return {
            'result': json.dumps(result_dict),
            'content_type': 'application/json'
        }

    except UsageCorrection.DoesNotExist:
        logger.error(f"UsageCorrection with id={usage_id} does not exist.")
        raise ValueError(f"UsageCorrection with id={usage_id} does not exist.")
    except SoftTimeLimitExceeded:
        logger.error(f"manual_correction_geojson_task (usage_id={usage_id}) time limit.")
        raise
    except Exception as e:
        logger.error(
            f"Manual correction geojson task failed (usage_id={usage_id}): {e}",
            exc_info=True
        )
        try:
            usage.set_status(StatusField.FAILED)
        except:
            pass
        raise


def _xml2sentences_helper(xml_str: str) -> str:
    """
    Minimal re-implementation of your _xml2sentences logic.
    Adjust as needed or import from your code.
    """
    try:
        parser = etree.XMLParser(recover=True)
        root = etree.fromstring(xml_str.encode('utf-8'), parser=parser)
    except etree.XMLSyntaxError as e:
        logger.error(f"XML parsing error: {e}")
        return ""

    paragraphs = []
    paragraph_elements = root.xpath('//p')
    if not paragraph_elements:
        paragraphs.append(''.join(root.itertext()))
    else:
        for elem in paragraph_elements:
            paragraphs.append(''.join(elem.itertext()))

    import re
    sentence_endings = re.compile(r'(?<=[.!?])\s+')
    sentences_all = []
    for paragraph in paragraphs:
        try:
            splitted = sentence_endings.split(paragraph.strip())
            sentences_all.extend(splitted)
        except Exception as e:
            logger.error(f"Sentence segmentation failed: {e}")
            sentences_all.append(paragraph)

    return "\n".join(sentences_all)


@shared_task(
    bind=True,
    queue='ocr_queue',
    time_limit=TIME_LIMIT,
    soft_time_limit=TIME_LIMIT - 10
)
def post_ocr_correction_task(self, usage_id: int, text: str, language: str, method_name: str,
                             prompt: str = None) -> dict:
    """
    Asynchronous Post-OCR correction task for SymSpell, SymSpellFlair, or LLM-based corrections.
    We reuse the CorrectionConnector's methods just like the sync version.
    Returns a dict with the corrected text in JSON format.
    """
    try:
        usage = UsageCorrection.objects.get(id=usage_id)
        usage.set_status(StatusField.IN_PROGRESS)

        connector = CorrectionConnector()
        if method_name == "sym_spell":
            correction = connector.correct_sym_spell(text, language)
        elif method_name == "sym_spell_flair":
            correction = connector.correct_sym_spell_flair(text, language)
        elif method_name == "llm":
            correction = connector.correct_llm(text, language, prompt=prompt)
        else:
            raise ValueError(f"Unknown method_name={method_name}")

        usage.set_status(StatusField.SUCCESS)
        usage.corrected_size = len(correction.text)
        usage.save()

        import json
        return {
            'result': json.dumps(correction.dict()),
            'content_type': 'application/json'
        }

    except UsageCorrection.DoesNotExist:
        logger.error(f"UsageCorrection with id={usage_id} does not exist.")
        raise ValueError(f"UsageCorrection with id={usage_id} does not exist.")
    except SoftTimeLimitExceeded:
        logger.error(f"post_ocr_correction_task (usage_id={usage_id}) time limit.")
        raise
    except Exception as e:
        logger.error(
            f"Post-OCR correction task failed (usage_id={usage_id}): {e}",
            exc_info=True
        )
        try:
            usage.set_status(StatusField.FAILED)
        except:
            pass
        # If fail, return fallback or just re-raise
        raise


@shared_task(
    bind=True,
    queue='ocr_queue',
    time_limit=TIME_LIMIT,
    soft_time_limit=TIME_LIMIT - 10
)
def correction_file_geojson_task(self, usage_id: int, file_bytes: bytes, language: str, option: str) -> dict:
    """
    Asynchronous version of CorrectionFileGeoJson.
    1) Retrieve UsageCorrection, set status = IN_PROGRESS
    2) parse file -> PageXML or text
    3) run correction
    4) build text + geojson + pagexml
    5) usage.set_status(StatusField.SUCCESS) or .FAILED
    6) return { 'result': json_string, 'content_type': 'application/json' }
    """

    def _xml2sentences(xml_str: str) -> str:
        try:
            parser = etree.XMLParser(recover=True)
            root = etree.fromstring(xml_str.encode('utf-8'), parser=parser)
        except etree.XMLSyntaxError as e:
            logger.error(f"XML parsing error: {e}", exc_info=True)
            return ""

        paragraph_elements = root.xpath('//p')
        paragraphs = []
        if not paragraph_elements:
            paragraphs.append(''.join(root.itertext()))
        else:
            for elem in paragraph_elements:
                paragraphs.append(''.join(elem.itertext()))

        import re
        sentence_endings = re.compile(r'(?<=[.!?])\s+')
        all_sentences = []
        for paragraph in paragraphs:
            try:
                splitted = sentence_endings.split(paragraph.strip())
                all_sentences.extend(splitted)
            except Exception as e:
                logger.error(f"Sentence segmentation error: {e}", exc_info=True)
                all_sentences.append(paragraph)

        return "\n".join(all_sentences)

    try:
        usage = UsageCorrection.objects.get(pk=usage_id)
        usage.set_status(StatusField.IN_PROGRESS)

        # Check if file_bytes is valid XML
        is_xml = False
        try:
            etree.fromstring(file_bytes)
            is_xml = True
        except Exception:
            pass

        if is_xml:
            # If it’s XML, parse into a PageXMLWrapper
            page_xml = PageXMLWrapper()
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(file_bytes)
                tmp.flush()
                tmp.seek(0)
                page_xml.parse(tmp.name)

            parser = PageXMLParagraphParser()
            parsed_segments = parser.forward(page_xml)
        else:
            # Not XML => treat as text
            original_content = file_bytes.decode("utf-8", errors="replace")
            parser = TextParagraphParser()
            parsed_segments = parser.forward(original_content)

        # pick the pipeline step from CorrectionEnum
        step_class = CorrectionEnum.get_step_class_from_name(option)
        step_instance = step_class(language)

        # run the pipeline
        corrected_segments = step_instance.forward(parsed_segments)

        # Reconstruct final result
        result_of_backward = parser.backward(corrected_segments)

        # FIX: If it's a PageXMLWrapper, convert to a string
        if isinstance(result_of_backward, PageXMLWrapper):
            corrected_str = str(result_of_backward)  # returns final XML string
        else:
            corrected_str = result_of_backward

        if is_xml:
            # corrected_str is updated PageXML
            text_result = _xml2sentences(corrected_str)
            from ocr.pagexml2geojson import main_from_xml_string
            geojson_result = main_from_xml_string(corrected_str)
            pagexml_result = corrected_str
        else:
            # corrected_str is plain text
            text_result = corrected_str
            geojson_result = {}
            pagexml_result = corrected_str

        usage.set_status(StatusField.SUCCESS)
        usage.corrected_size = len(corrected_str)
        usage.save()

        import json
        result_dict = {
            "text": text_result,
            "geojson": geojson_result,
            "pagexml": pagexml_result,
        }
        return {
            "result": json.dumps(result_dict),
            "content_type": "application/json"
        }

    except UsageCorrection.DoesNotExist:
        logger.error(f"UsageCorrection {usage_id} not found")
        raise
    except Exception as e:
        logger.error(f"correction_file_geojson_task failed: {e}", exc_info=True)
        try:
            usage.set_status(StatusField.FAILED)
        except:
            pass
        raise
