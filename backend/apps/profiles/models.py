from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=40, blank=True)
    birth_year = models.PositiveSmallIntegerField(default=1999)
    job_status = models.CharField(max_length=40, blank=True, default="employed")
    annual_income = models.PositiveIntegerField(default=0)
    asset = models.PositiveIntegerField(default=0)
    debt = models.PositiveIntegerField(default=0)
    monthly_saving = models.PositiveIntegerField(default=0)
    is_homeless = models.BooleanField(default=True)
    subscription_months = models.PositiveSmallIntegerField(default=0)
    special_conditions = models.JSONField(default=list, blank=True)
    preferred_regions = models.JSONField(default=list, blank=True)
    preferred_supply_types = models.JSONField(default=list, blank=True)
    target_months = models.PositiveSmallIntegerField(default=18)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name or f"profile-{self.pk}"


class Favorite(models.Model):
    FAVORITE_TYPES = [
        ("notice", "Notice"),
        ("product", "Product"),
        ("policy", "Policy"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    client_id = models.CharField(max_length=64, blank=True, db_index=True)
    favorite_type = models.CharField(max_length=20, choices=FAVORITE_TYPES)
    object_id = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "favorite_type", "object_id"],
                name="unique_user_favorite",
            ),
            models.UniqueConstraint(
                fields=["client_id", "favorite_type", "object_id"],
                name="unique_client_favorite",
            )
        ]

    def __str__(self) -> str:
        return f"{self.favorite_type}:{self.object_id}"
