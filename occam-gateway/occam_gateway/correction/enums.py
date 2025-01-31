# correction/enums.py

from enum import Enum
from typing import Optional, Type
from pydantic import BaseModel
from shared.pipeline import (
    OCRCorrectionLLMStep,
    OCRCorrectionSymSpellFlairStep,
    OCRCorrectionSymSpellStep,
    PipelineStep,
)

class CorrectionInfo(BaseModel):
    step_class: Type[PipelineStep]
    name: str
    description: Optional[str]


class CorrectionEnum(Enum):
    SYMSPELL = CorrectionInfo(
        step_class=OCRCorrectionSymSpellStep,
        name="Correction (SymSpell)",
        description="Post-OCR correction using SymSpell",
    )
    SYMSPELL_FLAIR = CorrectionInfo(
        step_class=OCRCorrectionSymSpellFlairStep,
        name="Correction (SymSpell + Flair)",
        description="Post-OCR correction using SymSpell and Flair",
    )
    LLM = CorrectionInfo(
        step_class=OCRCorrectionLLMStep,
        name="Correction (LLM)",
        description="Post-OCR correction using a Large Language Model (LLM)",
    )

    @staticmethod
    def get_representation():
        return [
            {
                "name": step.value.name,
                "description": step.value.description,
            }
            for step in CorrectionEnum
        ]

    @staticmethod
    def get_step_class_from_name(name):
        return next(
            step.value.step_class
            for step in CorrectionEnum
            if step.value.name.lower() == name.lower()
        )
