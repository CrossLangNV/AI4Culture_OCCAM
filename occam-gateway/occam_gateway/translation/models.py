# Create your models here.
from django.db.models import IntegerField, CharField

from organisation.models import OrganisationAPIKey
from shared.models import UsageShared


class UsageTranslationSnippet(UsageShared):
    """
    keep track of the usage of translation of snippets
    """

    source_size = IntegerField()
    target_size = IntegerField(null=True, blank=True)

    source_language = CharField(max_length=10)
    target_language = CharField(max_length=10)


class UsageTranslationFile(UsageShared):
    """
    keep track of the usage of translation of files
    """

    source_size = IntegerField()
    target_size = IntegerField(null=True, blank=True)

    source_language = CharField(max_length=10)
    target_language = CharField(max_length=10)
