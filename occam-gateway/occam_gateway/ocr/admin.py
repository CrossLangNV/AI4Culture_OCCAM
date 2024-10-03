from django.contrib import admin

from .models import OCREngine, UsageOCR


@admin.register(OCREngine)
class OCREngineAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]
    search_fields = ["name"]


@admin.register(UsageOCR)
class UsageOCRAdmin(admin.ModelAdmin):
    list_display = ["api_key", "status", "date", "ocr_engine"]
    readonly_fields = ["api_key", "ocr_engine"]
