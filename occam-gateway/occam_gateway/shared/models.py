from django.db import models

from organisation.models import OrganisationAPIKey


class StatusField(models.CharField):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

    _STATUS_CHOICES = [
        (PENDING, "Pending"),
        (IN_PROGRESS, "In progress"),
        (SUCCESS, "Success"),
        (FAILED, "Failed"),
    ]

    def __init__(self, *args, max_length=100, choices=None, default=PENDING, **kwargs):
        super().__init__(
            *args,
            **kwargs,
            max_length=max_length,
            choices=self._STATUS_CHOICES,
            default=default,
        )

    def ready(self, value) -> bool:
        """
        Tells whether the task is finished or not (SUCCESS or FAILED)
        :return:
        """

        return value in [self.SUCCESS, self.FAILED]


class UsageShared(models.Model):
    """
    keep track of the usage of the OCR API
    """

    # Do not delete if user is deleted
    api_key = models.ForeignKey(
        OrganisationAPIKey,
        on_delete=models.SET_NULL,
        null=True,
        # Don't allow to change the API key
        editable=False,
    )

    # Metadata
    status = StatusField()

    # Date and time of the request
    date = models.DateTimeField(auto_now_add=True)

    def set_status(self, status: StatusField):
        """
        Set the status of the usage
        """
        self.status = status
        self.save(update_fields=["status"])

    class Meta:
        abstract = True
