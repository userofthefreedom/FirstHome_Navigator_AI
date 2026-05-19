from django.db import models


class FinancialProduct(models.Model):
    name = models.CharField(max_length=120)
    provider = models.CharField(max_length=60)
    category = models.CharField(max_length=40)
    rate = models.CharField(max_length=40, blank=True)
    monthly_limit = models.PositiveIntegerField(default=0)
    term_months = models.PositiveSmallIntegerField(default=0)
    protection_status = models.BooleanField(default=True)
    source_url = models.URLField(blank=True)
    reasons = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.provider} {self.name}"
