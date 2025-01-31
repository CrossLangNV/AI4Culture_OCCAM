import os
import subprocess
import tempfile
from typing import Optional
import logging
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

app = FastAPI()

logger = logging.getLogger(__name__)


class OCRResult(BaseModel):
    name: Optional[str] = None
    xml: str
    text: Optional[str] = None


"""
The model gets loaded with every call, by calling OCR as a user-scripts 
"""


@app.post("/ocr",
          response_model=OCRResult
          )
async def ocr_image(
        image: UploadFile = File(...)
):
    filename = image.filename

    with tempfile.TemporaryDirectory() as dirpath:
        filename_image_tmp = os.path.join(dirpath, filename)
        with open(filename_image_tmp, 'wb') as f_image:
            f_image.write(await image.read())

        filename_xml = os.path.join(dirpath, 'page.xml')
        filename_txt = os.path.join(dirpath, 'page.txt')

        a = subprocess.run(['python', '-m', 'scripts.run_foo',
                            '-f', filename_image_tmp,
                            '-x', filename_xml,
                            '-t', filename_txt
                            ])
        if a.returncode != 0:
            logger.error("OCR script failed")
            logger.info(a.stdout)

        with open(filename_xml) as f:
            xml = f.read()

        with open(filename_txt) as f:
            text = f.read()

    result = OCRResult(xml=xml,
                       name=filename,
                       text=text)

    return result
