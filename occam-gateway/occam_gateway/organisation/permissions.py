import logging

from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework_api_key.permissions import BaseHasAPIKey

from .models import OrganisationAPIKey

logger = logging.getLogger(__name__)


class HasOrganisationAPIKey(BaseHasAPIKey):
    model = OrganisationAPIKey


class IsAuthenticatedOrHasAPIKey(BasePermission):
    """
    Grant access if user is authenticated OR has a valid API key.
    """

    def has_permission(self, request, view):
        # If IsAuthenticated passes, return True
        if IsAuthenticated().has_permission(request, view):
            return True
        # Else check HasOrganisationAPIKey
        return HasOrganisationAPIKey().has_permission(request, view)


class IsAuthenticatedOrHasAPIKeyDebug(BaseHasAPIKey):
    model = OrganisationAPIKey

    def has_permission(self, request, view):
        # Print/log the incoming headers:
        logger.debug("---- Headers ----")
        for k, v in request.headers.items():
            logger.debug("%s: %s", k, v)

        # Now let the parent class handle normal logic
        result = super().has_permission(request, view)

        logger.debug("APIKey permission result: %s", result)
        return result

    def get_key(self, request):
        """
        Extracts the raw key string from the request headers.
        We'll add debug logs to see what it returns.
        """
        raw_key = super().get_key(request)
        logger.debug("Extracted raw_key = %s", raw_key)
        return raw_key
