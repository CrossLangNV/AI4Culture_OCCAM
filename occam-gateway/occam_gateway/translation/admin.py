from django.contrib import admin

from translation.models import UsageTranslationSnippet, UsageTranslationFile


@admin.register(UsageTranslationSnippet)
class UsageOCRAdmin(admin.ModelAdmin):
    list_display = ["api_key", "status", "date", "source_language", "target_language"]
    readonly_fields = ["api_key"]

@admin.register(UsageTranslationFile)
class UsageOCRAdmin(admin.ModelAdmin):
    list_display = ["api_key", "status", "date", "source_language", "target_language"]
    readonly_fields = ["api_key"]
