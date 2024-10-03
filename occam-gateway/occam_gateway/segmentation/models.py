from django.db import models

from shared.models import UsageShared


class UsageSegmentation(UsageShared):
    """
    keep track of the usage of the Correction API
    """

    # Anonymized information about the request
    source_language = models.CharField(max_length=10, blank=True, null=True)
    source_size = models.PositiveIntegerField(blank=True, null=True)

    # Anonymized information about the response
    target_size = models.PositiveIntegerField(blank=True, null=True)
