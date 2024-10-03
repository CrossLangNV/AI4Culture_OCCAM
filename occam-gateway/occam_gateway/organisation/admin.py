from django.contrib import admin
from rest_framework_api_key.admin import APIKeyModelAdmin

from organisation.models import Organisation, OrganisationAPIKey


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ["name", "active"]
    list_filter = ["active"]
    search_fields = ["name"]


@admin.register(OrganisationAPIKey)
class OrganisationApiKeysAdmin(APIKeyModelAdmin):
    list_display = [*APIKeyModelAdmin.list_display, "get_organisation_name"]
    search_fields = [*APIKeyModelAdmin.search_fields, "organisation__name"]

    def get_organisation_name(self, obj):
        return obj.organisation.name

    get_organisation_name.short_description = (
        "Organisation Name"  # Sets column name in admin interface
    )
