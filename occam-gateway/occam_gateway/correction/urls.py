from django.urls import path

from .views import (
    PostOCRSymSpellAPIView,
    PostOCRSymSpellFlairAPIView,
    PostOCRLLMAPIView,
    CorrectionOptionsAPIView,
    CorrectionFileAPIView, OCRManualCorrectionAPIView, OCRManualCorrectionGeoJsonAPIView,
    OCRManualCorrectionStringInputAPIView, CorrectionJobStatusAPIView, CorrectionJobResultAPIView,
    CorrectionFileGeoJsonAPIView,
)

urlpatterns = [
    path("manual/", OCRManualCorrectionStringInputAPIView.as_view(), name="manual"),
    path("manual/file", OCRManualCorrectionAPIView.as_view(), name="manual_file"),
    path("manual/geojson", OCRManualCorrectionGeoJsonAPIView.as_view(), name="manual_geojson"),
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
        "file/geojson",
        CorrectionFileGeoJsonAPIView.as_view(),
        name="file_geojson",
    ),
    path(
        "file/options/",
        CorrectionOptionsAPIView.as_view(),
        name="options",
    ),
    path('status/<str:task_id>/', CorrectionJobStatusAPIView.as_view(), name='correction-job-status'),
    path('result/<str:task_id>/', CorrectionJobResultAPIView.as_view(), name='correction-job-result'),
]
