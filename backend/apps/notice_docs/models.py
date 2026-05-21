from django.db import models

from apps.notices.models import HousingNotice


class NoticeDocument(models.Model):
    STATUS_CHOICES = [
        ("discovered", "Discovered"),
        ("pending", "Pending"),
        ("analyzed", "Analyzed"),
        ("failed", "Failed"),
    ]

    notice = models.ForeignKey(HousingNotice, on_delete=models.CASCADE, related_name="documents")
    provider = models.CharField(max_length=40, blank=True)
    file_id = models.CharField(max_length=120, blank=True, db_index=True)
    file_name = models.CharField(max_length=220, blank=True)
    document_url = models.URLField(blank=True)
    source_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="discovered", db_index=True)
    error_message = models.CharField(max_length=240, blank=True)
    fetched_at = models.DateTimeField(null=True, blank=True)
    analyzed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.file_name or f"notice-document-{self.pk}"


class NoticeExtraction(models.Model):
    STATUS_CHOICES = [
        ("mock", "Mock"),
        ("pending", "Pending"),
        ("valid", "Valid"),
        ("needs_review", "Needs review"),
        ("failed", "Failed"),
    ]

    notice = models.ForeignKey(HousingNotice, on_delete=models.CASCADE, related_name="extractions")
    document = models.ForeignKey(NoticeDocument, on_delete=models.CASCADE, related_name="extractions")
    schema_version = models.CharField(max_length=20, default="mock-v1")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="mock")
    confidence = models.FloatField(default=0)
    raw_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.notice_id}:{self.schema_version}:{self.status}"


class HousingUnitOption(models.Model):
    notice = models.ForeignKey(HousingNotice, on_delete=models.CASCADE, related_name="unit_options")
    document = models.ForeignKey(NoticeDocument, on_delete=models.SET_NULL, null=True, blank=True, related_name="unit_options")
    extraction = models.ForeignKey(NoticeExtraction, on_delete=models.SET_NULL, null=True, blank=True, related_name="unit_options")
    unit_type = models.CharField(max_length=40)
    exclusive_area_m2 = models.FloatField(default=0)
    floor_group = models.CharField(max_length=40, blank=True)
    option_type = models.CharField(max_length=40, default="basic")
    base_price = models.PositiveBigIntegerField(default=0)
    loan_amount = models.PositiveBigIntegerField(default=0)
    balcony_extension_price = models.PositiveBigIntegerField(default=0)
    confidence = models.FloatField(default=0)
    source_page = models.PositiveSmallIntegerField(null=True, blank=True)
    source_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["notice", "unit_type", "floor_group", "option_type"],
                name="unique_notice_unit_option",
            )
        ]
        ordering = ["exclusive_area_m2", "unit_type", "floor_group", "id"]

    def __str__(self) -> str:
        return f"{self.notice.title} {self.unit_type}"


class PaymentSchedule(models.Model):
    PAYMENT_TYPES = [
        ("application", "Application"),
        ("winner", "Winner"),
        ("down_payment", "Down payment"),
        ("middle_payment", "Middle payment"),
        ("final_payment", "Final payment"),
        ("loan", "Loan"),
        ("other", "Other"),
    ]

    unit_option = models.ForeignKey(HousingUnitOption, on_delete=models.CASCADE, related_name="payment_schedules")
    label = models.CharField(max_length=80)
    due_date = models.DateField(null=True, blank=True)
    amount = models.PositiveBigIntegerField(default=0)
    payment_type = models.CharField(max_length=24, choices=PAYMENT_TYPES, default="other")
    sequence = models.PositiveSmallIntegerField(default=0)
    evidence_text = models.TextField(blank=True)

    class Meta:
        ordering = ["sequence", "due_date", "id"]

    def __str__(self) -> str:
        return f"{self.unit_option_id}:{self.label}"


class EligibilityChecklist(models.Model):
    notice = models.ForeignKey(HousingNotice, on_delete=models.CASCADE, related_name="eligibility_checklists")
    document = models.ForeignKey(NoticeDocument, on_delete=models.SET_NULL, null=True, blank=True, related_name="eligibility_checklists")
    category = models.CharField(max_length=40)
    title = models.CharField(max_length=120)
    condition_text = models.TextField()
    evidence_text = models.TextField(blank=True)
    confidence = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "id"]

    def __str__(self) -> str:
        return f"{self.notice_id}:{self.title}"


class ExtractionEvidence(models.Model):
    extraction = models.ForeignKey(NoticeExtraction, on_delete=models.CASCADE, related_name="evidence")
    field_path = models.CharField(max_length=160)
    page_no = models.PositiveSmallIntegerField(null=True, blank=True)
    source_text = models.TextField()
    confidence = models.FloatField(default=0)

    def __str__(self) -> str:
        return f"{self.extraction_id}:{self.field_path}"
