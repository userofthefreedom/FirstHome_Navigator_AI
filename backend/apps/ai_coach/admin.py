from django.contrib import admin

from apps.ai_coach.models import AiChatLog, AiExtractionResult


@admin.register(AiExtractionResult)
class AiExtractionResultAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "source_type",
        "source_id",
        "source_title",
        "extraction_type",
        "status",
        "model_name",
        "prompt_version",
        "updated_at",
    )
    list_filter = ("source_type", "extraction_type", "status", "model_name", "prompt_version")
    search_fields = ("source_title", "source_url", "input_hash", "error_message")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AiChatLog)
class AiChatLogAdmin(admin.ModelAdmin):
    list_display = ("id", "notice_id", "option_id", "provider", "model_name", "created_at")
    list_filter = ("provider", "model_name")
    search_fields = ("question", "answer", "error_message")
    readonly_fields = ("created_at",)
