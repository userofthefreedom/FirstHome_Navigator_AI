from django.conf import settings
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
    product_code = models.CharField(max_length=80, blank=True, db_index=True)
    bank_code = models.CharField(max_length=40, blank=True)
    join_way = models.TextField(blank=True)
    special_condition = models.TextField(blank=True)
    source_meta = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["provider", "name", "category"], name="unique_financial_product")
        ]

    def __str__(self) -> str:
        return f"{self.provider} {self.name}"


class FinancialProductOption(models.Model):
    product = models.ForeignKey(FinancialProduct, related_name="options", on_delete=models.CASCADE)
    save_trm = models.PositiveSmallIntegerField(default=0)
    intr_rate_type = models.CharField(max_length=40, blank=True)
    intr_rate_type_nm = models.CharField(max_length=80, blank=True)
    intr_rate = models.FloatField(default=0)
    intr_rate2 = models.FloatField(default=0)
    rsrv_type = models.CharField(max_length=40, blank=True)
    rsrv_type_nm = models.CharField(max_length=80, blank=True)
    source_meta = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "save_trm", "intr_rate_type", "rsrv_type"],
                name="unique_financial_product_option",
            )
        ]
        ordering = ["save_trm", "-intr_rate2", "-intr_rate", "id"]

    def __str__(self) -> str:
        return f"{self.product} {self.save_trm}m {self.intr_rate2 or self.intr_rate}%"


class UserJoinedProduct(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="joined_products", on_delete=models.CASCADE)
    product = models.ForeignKey(FinancialProduct, related_name="joined_users", on_delete=models.CASCADE)
    selected_option = models.ForeignKey(
        FinancialProductOption,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="joined_users",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    memo = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="unique_user_joined_product")
        ]
        ordering = ["-joined_at", "-id"]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.product_id}"


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
