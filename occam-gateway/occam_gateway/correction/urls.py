from django.urls import path

from .views import (
    PostOCRSymSpellAPIView,
    PostOCRSymSpellFlairAPIView,
    PostOCRLLMAPIView,
    CorrectionOptionsAPIView,
    CorrectionFileAPIView, OCRManualCorrectionAPIView,
)

urlpatterns = [
    path("manual/", OCRManualCorrectionAPIView.as_view(), name="manual"),
    path(
        "sym_spell/",
        PostOCRSymSpellAPIView.as_view(),
        name="sym_spell",
    ),
    path(
        "sym_spell_flair/",
        PostOCRSymSpellFlairAPIView.as_view(),
        name="sym_spell_flair",
    ),
    path(
        "llm/",
        PostOCRLLMAPIView.as_view(),
        name="llm",
    ),
    path(
        "file/",
        CorrectionFileAPIView.as_view(),
        name="file",
    ),
    path(
        "file/options/",
        CorrectionOptionsAPIView.as_view(),
        name="options",
    ),
]
