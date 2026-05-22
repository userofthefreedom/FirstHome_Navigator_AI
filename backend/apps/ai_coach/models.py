from django.db import models
from django.db.models import Q


class AiExtractionResult(models.Model):
    SOURCE_TYPES = [
        ("notice", "Housing notice"),
        ("policy", "Youth policy"),
        ("product", "Financial product"),
        ("document", "Document"),
    ]
    EXTRACTION_TYPES = [
        ("housing_notice", "Housing notice fields"),
        ("youth_policy", "Youth policy fields"),
        ("financial_product", "Financial product fields"),
        ("generic_document", "Generic document fields"),
    ]
    STATUSES = [
        ("pending", "Pending"),
        ("succeeded", "Succeeded"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    ]

    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES, db_index=True)
    source_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    source_title = models.CharField(max_length=200, blank=True)
    source_url = models.URLField(blank=True)
    extraction_type = models.CharField(max_length=40, choices=EXTRACTION_TYPES, db_index=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="pending", db_index=True)
    model_name = models.CharField(max_length=80, blank=True)
    prompt_version = models.CharField(max_length=40, default="firsthome-extract-v1")
    input_hash = models.CharField(max_length=64, blank=True, db_index=True)
    extracted_data = models.JSONField(default=dict, blank=True)
    confidence = models.JSONField(default=dict, blank=True)
    missing_fields = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["source_type", "source_id", "extraction_type"]),
            models.Index(fields=["status", "updated_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["source_type", "source_id", "extraction_type", "input_hash"],
                condition=Q(source_id__isnull=False) & ~Q(input_hash=""),
                name="unique_ai_extraction_input",
            ),
        ]

    def __str__(self) -> str:
        source = self.source_title or f"{self.source_type}:{self.source_id or 'external'}"
        return f"{source} / {self.extraction_type} / {self.status}"

    def mark_succeeded(
        self,
        *,
        extracted_data: dict,
        confidence: dict | None = None,
        missing_fields: list[str] | None = None,
        warnings: list[str] | None = None,
        raw_response: dict | None = None,
    ) -> None:
        self.status = "succeeded"
        self.extracted_data = extracted_data
        self.confidence = confidence or {}
        self.missing_fields = missing_fields or []
        self.warnings = warnings or []
        self.raw_response = raw_response or {}
        self.error_message = ""
        self.save()

    def mark_failed(self, message: str, *, raw_response: dict | None = None) -> None:
        self.status = "failed"
        self.error_message = message
        self.raw_response = raw_response or {}
        self.save()


class AiChatLog(models.Model):
    notice_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    option_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    question = models.TextField()
    answer = models.TextField(blank=True)
    provider = models.CharField(max_length=40, default="template")
    model_name = models.CharField(max_length=80, blank=True)
    source_refs = models.JSONField(default=list, blank=True)
    safety_flags = models.JSONField(default=list, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["notice_id", "option_id", "created_at"], name="ai_coach_ai_notice__f6c1b1_idx"),
        ]

    def __str__(self) -> str:
        return f"chat:{self.notice_id or 'none'}:{self.provider}"
