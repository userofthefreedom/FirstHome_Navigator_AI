from django.db import models


class HousingNotice(models.Model):
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
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title
