from django.db import models


class HousingNotice(models.Model):
    OWNERSHIP_TYPES = [
        ("unknown", "Unknown"),
        ("public_sale", "Public sale"),
        ("newlywed_public_sale", "Newlywed public sale"),
        ("private_participation_public_sale", "Private participation public sale"),
        ("excluded", "Excluded"),
    ]

    DOCUMENT_STATUSES = [
        ("not_requested", "Not requested"),
        ("pending", "Pending"),
        ("analyzed", "Analyzed"),
        ("failed", "Failed"),
    ]

    source_id = models.CharField(max_length=80, blank=True, db_index=True)
    title = models.CharField(max_length=120)
    provider = models.CharField(max_length=60)
    region = models.CharField(max_length=40)
    district = models.CharField(max_length=80)
    supply_type = models.CharField(max_length=40)
    housing_type = models.CharField(max_length=40)
    area = models.CharField(max_length=20, blank=True)
    price = models.PositiveIntegerField(default=0)
    contract_rate = models.FloatField(default=0.1)
    application_deadline = models.DateField()
    winner_date = models.DateField(null=True, blank=True)
    contract_date = models.DateField(null=True, blank=True)
    move_in = models.CharField(max_length=20, blank=True)
    competition = models.CharField(max_length=40, blank=True)
    source_url = models.URLField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    required_documents = models.JSONField(default=list, blank=True)
    cautions = models.JSONField(default=list, blank=True)
    source_meta = models.JSONField(default=dict, blank=True)
    ownership_type = models.CharField(max_length=40, choices=OWNERSHIP_TYPES, default="unknown", db_index=True)
    is_service_target = models.BooleanField(default=False, db_index=True)
    exclude_reason = models.CharField(max_length=160, blank=True)
    official_document_status = models.CharField(max_length=24, choices=DOCUMENT_STATUSES, default="not_requested")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title
