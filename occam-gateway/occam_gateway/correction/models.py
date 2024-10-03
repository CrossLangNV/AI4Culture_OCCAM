from django.db import models

from organisation.models import OrganisationAPIKey
from shared.models import UsageShared


class UsageCorrection(UsageShared):
    """
    keep track of the usage of the Correction API
    """

    method = models.CharField(max_length=100)

    # Anonymized information about the request
    source_language = models.CharField(max_length=10, blank=True, null=True)
    source_size = models.PositiveIntegerField(blank=True, null=True)
    # extra custom field
    extra = models.JSONField(blank=True, null=True)

    # Anonymized information about the response
    corrected_size = models.PositiveIntegerField(blank=True, null=True)
