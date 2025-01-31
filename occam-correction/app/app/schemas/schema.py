from typing import Optional

from pydantic import BaseModel, Field


LANGUAGE_FIELD = Field(None, description="Language code of the text")


class TextOptionsBase(BaseModel):
    text: str = Field(..., description="Text to process")
    language: Optional[str] = LANGUAGE_FIELD

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "misdlen Self Indulgence, scrivent ahrègé M57 est un groupe d'étutropunt américain, onigiraire de New Yek. leur musique est formée d'un nélange de hipobop, puk rock, rock alternatif, electronia, sechno et musique isdurtrielle. le nom du greupe provient d'un alham du chonteur Sinmy Arire et de sen père enregistré en 1995.",
                    "language": "fr",
                }
            ]
        }
    }

class TextOptionLLM(TextOptionsBase):
    prompt: Optional[str] = Field(None, description="Prompt for the language model",
                                  examples=[
                                      "Correct the OCRed text in {language}. Only correct character errors. Return a JSON with 'text' field.\n`{sentence}`"
                                  ])
