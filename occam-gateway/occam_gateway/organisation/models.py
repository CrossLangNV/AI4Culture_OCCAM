from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import (
    PermissionsMixin,
)
from django.db import models
from rest_framework_api_key.models import AbstractAPIKey, BaseAPIKeyManager


class OrganisationAPIKeyManager(BaseAPIKeyManager):
    def get_usable_keys(self):
        return super().get_usable_keys().filter(organisation__active=True)

    def get_from_request(self, request):
        key = request.META.get("HTTP_API_KEY")
        if not key:
            raise self.AuthException("No API key found")

        return self.get_from_key(key)

    class AuthException(Exception):
        pass


class Organisation(models.Model):
    name = models.CharField(max_length=128)
    active = models.BooleanField(default=True)


class OrganisationAPIKey(AbstractAPIKey):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )

    objects = OrganisationAPIKeyManager()

    # ...
    class Meta(AbstractAPIKey.Meta):
        verbose_name = "Organisation API key"
        verbose_name_plural = "Organisation API keys"
