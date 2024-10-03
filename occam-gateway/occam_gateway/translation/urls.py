from django.urls import path

from .views import (
    TranslatePipelineOptionsAPIView,
    TranslationJobStatusAPIView, TranslationJobResultAPIView,
    CombinedTranslateSnippetAPIView, CombinedTranslateFileAPIView, CombinedTranslatePipelineBatchAPIView,
)

urlpatterns = [
    path(
        "snippet",
        CombinedTranslateSnippetAPIView.as_view(),
        name="snippet",
    ),
    path(
        "file",
        CombinedTranslateFileAPIView.as_view(),
        name="file",
    ),
    path("batch",
         CombinedTranslatePipelineBatchAPIView.as_view(),
         name="batch"),
    path(
        "options",
        TranslatePipelineOptionsAPIView.as_view(),
        name="pipeline_options",
    ),
    path('status/<task_id>/', TranslationJobStatusAPIView.as_view(), name='translation_status'),
    path('result/<task_id>/', TranslationJobResultAPIView.as_view(), name='translation_result'),
]
