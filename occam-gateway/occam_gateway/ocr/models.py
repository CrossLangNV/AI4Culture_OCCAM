from django.db import models

from organisation.models import OrganisationAPIKey
from shared.models import UsageShared


class OCREngine(models.Model):
    """
    OCR Engine,
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class UsageOCR(UsageShared):
    """
    keep track of the usage of the OCR API
    """

    ocr_engine = models.ForeignKey(
        OCREngine,
        on_delete=models.SET_NULL,
        null=True,
        # Don't allow to change the OCR engine
        editable=False,
    )

    # Anonymized information about the request
    image_size = models.PositiveIntegerField(blank=True, null=True)

    # Anonymized information about the response
    overlay_size = models.PositiveIntegerField(blank=True, null=True)

    def set_image_size(self, image_size: int):
        """
        Set the image size
        """
        self.image_size = image_size
        self.save(update_fields=["image_size"])

    def set_overlay_size(self, overlay_size: int):
        """
        Set the overlay size
        """
        self.overlay_size = overlay_size
        self.save(update_fields=["overlay_size"])
