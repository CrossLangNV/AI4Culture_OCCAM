import logging

from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework_api_key.permissions import BaseHasAPIKey

from .models import OrganisationAPIKey

logger = logging.getLogger(__name__)


class HasOrganisationAPIKey(BaseHasAPIKey):
    model = OrganisationAPIKey


def get_optional_organisation_api_key(request):
    raw_key = request.META.get("HTTP_API_KEY")
    if not raw_key:
        return None

    try:
        return OrganisationAPIKey.objects.get_from_key(raw_key)
    except Exception:
        if getattr(request.user, "is_authenticated", False):
            return None
        raise


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


class IsAuthenticatedOrHasAPIKeyDebug(BasePermission):
    def has_permission(self, request, view):
        # Print/log the incoming headers:
        logger.debug("---- Headers ----")
        for k, v in request.headers.items():
            logger.debug("%s: %s", k, v)

        result = IsAuthenticatedOrHasAPIKey().has_permission(request, view)

        logger.debug("Auth/API key permission result: %s", result)
        return result
