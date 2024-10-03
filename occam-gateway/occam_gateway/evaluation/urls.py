from django.urls import path

from .views import OCREvalAPIView, OCREvalTextAPIView

urlpatterns = [
    path(
        "OCR/eval",
        OCREvalAPIView.as_view(),
        name="OCR-eval",
    ),
    path(
        "OCR/eval/text",
        OCREvalTextAPIView.as_view(),
        name="OCR-eval-text",
    ),
]
