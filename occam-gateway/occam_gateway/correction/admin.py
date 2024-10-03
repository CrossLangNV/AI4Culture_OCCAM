from django.contrib import admin

from .models import UsageCorrection


@admin.register(UsageCorrection)
class UsageCorrectionAdmin(admin.ModelAdmin):
    list_display = ["api_key", "status", "date", "source_language", "method"]
    readonly_fields = ["api_key"]
