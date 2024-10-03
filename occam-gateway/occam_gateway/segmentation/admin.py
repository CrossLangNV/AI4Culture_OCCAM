from django.contrib import admin

from .models import UsageSegmentation


@admin.register(UsageSegmentation)
class UsageCorrectionAdmin(admin.ModelAdmin):
    list_display = ["api_key", "status", "date", "source_language"]
    readonly_fields = ["api_key"]
