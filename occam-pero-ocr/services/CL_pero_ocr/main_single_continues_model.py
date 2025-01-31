import traceback
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from pero_ocr.document_ocr.layout import PageLayout
from pydantic import BaseModel

from src.dump import get_image, image_folder_name, layout_model_name, get_engine, ocr_model_name
from configs.parser import configuration_pero_ocr

app = FastAPI()


class OCRResult(BaseModel):
    name: Optional[str] = None
    xml: str
    text: Optional[str] = None


config = configuration_pero_ocr(image_folder_name, layout_model_name, ocr_model_name)
page_parser, engine_name, engine_version = get_engine(config=config, headers=None, engine_id=None)


@app.post("/ocr",
          response_model=OCRResult
          )
async def ocr_image(
        image: UploadFile = File(...)
):
    filename = image.filename

    print('-- Load image --')
    contents = await image.read()
    img = get_image(contents)

    print('-- Process image --')
    # Process image
    try:
        page_layout = PageLayout(id=filename,
                                 page_size=img.shape[:2],
                                 )

        page_layout = page_parser.process_page(img, page_layout)

    except:
        exception = traceback.format_exc()
        raise HTTPException(status_code=420,
                            detail=exception
                            )

    def get_page_layout_text(page_layout):
        text = ""
        for line in page_layout.lines_iterator():
            text += "{}\n".format(line.transcription)
        return text

    xml = page_layout.to_pagexml_string()
    text = get_page_layout_text(page_layout)

    result = OCRResult(xml=xml,
                       name=filename,
                       text=text)

    return result
