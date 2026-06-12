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


class LoanProduct(models.Model):
    name = models.CharField(max_length=160)
    provider = models.CharField(max_length=80)
    category = models.CharField(max_length=40, default="주택담보대출")
    loan_purpose = models.CharField(max_length=40, default="purchase")
    description = models.TextField(blank=True)
    target = models.CharField(max_length=200, blank=True)
    rate = models.CharField(max_length=80, blank=True)
    limit = models.CharField(max_length=120, blank=True)
    limit_amount = models.PositiveBigIntegerField(default=0)
    term = models.CharField(max_length=80, blank=True)
    term_years = models.PositiveSmallIntegerField(default=30)
    age_min = models.PositiveSmallIntegerField(default=19)
    age_max = models.PositiveSmallIntegerField(default=70)
    max_income = models.PositiveBigIntegerField(default=0)
    max_price = models.PositiveBigIntegerField(default=0)
    max_area_m2 = models.FloatField(default=0)
    requires_homeless = models.BooleanField(default=False)
    source_url = models.URLField(blank=True)
    reasons = models.JSONField(default=list, blank=True)
    caveats = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["provider", "name", "category"], name="unique_loan_product")
        ]

    def __str__(self) -> str:
        return f"{self.provider} {self.name}"
