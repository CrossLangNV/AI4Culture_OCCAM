from django.urls import path

from .views import (
    SegmentationPipelineAPIView,
    SegmentationFileAPIView,
)

urlpatterns = [
    path(
        "pipeline/",
        SegmentationPipelineAPIView.as_view(),
        name="pipeline",
    ),
    path(
        "file/",
        SegmentationFileAPIView.as_view(),
        name="file",
    ),
]
