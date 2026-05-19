from django.db import models


class YouthPolicy(models.Model):
    name = models.CharField(max_length=120)
    provider = models.CharField(max_length=60)
    target = models.CharField(max_length=160)
    benefit = models.TextField(blank=True)
    policy_category = models.CharField(max_length=40, blank=True)
    regions = models.JSONField(default=list, blank=True)
    age_min = models.PositiveSmallIntegerField(default=19)
    age_max = models.PositiveSmallIntegerField(default=39)
    max_income = models.PositiveIntegerField(default=0)
    requires_homeless = models.BooleanField(default=False)
    source_url = models.URLField(blank=True)
    reasons = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name
