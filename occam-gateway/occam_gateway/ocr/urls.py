from django.urls import path

from ocr.views import OCREngineListView, OCRPipelineOptionsAPIView, \
    OCRJobStatusAPIView, OCRJobResultAPIView, OCRHealthCheckAPIView, \
    CombinedOCRAPIView, CombinedOCRFromURLAPIView

urlpatterns = [
    path("health", OCRHealthCheckAPIView.as_view(), name="health"),
    path(
        "engines",
        OCREngineListView.as_view(),
        name="engines",
    ),
    path(
        "image",
        CombinedOCRAPIView.as_view(),
        name="image",
    ),
    path(
        "image/url",
        CombinedOCRFromURLAPIView.as_view(),
        name="image_url",
    ),
    path(
        "options",
        OCRPipelineOptionsAPIView.as_view(),
        name="pipeline_options",
    ),
    path("status/<task_id>/", OCRJobStatusAPIView.as_view(), name="ocr_status"),
    path("result/<task_id>/", OCRJobResultAPIView.as_view(), name="ocr_result"),

]
