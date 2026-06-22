from django.db import models


class MarketAssetPrice(models.Model):
    asset_type = models.CharField(max_length=40, db_index=True)
    base_date = models.DateField(db_index=True)
    region_code = models.CharField(max_length=10, blank=True, db_index=True)
    region_name = models.CharField(max_length=80, blank=True)
    price = models.FloatField(default=0)
    change_rate = models.FloatField(default=0)
    source = models.CharField(max_length=80, blank=True)
    source_meta = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["asset_type", "base_date", "region_code"], name="unique_market_asset_price")
        ]
        ordering = ["base_date"]

    def __str__(self) -> str:
        return f"{self.asset_type}:{self.base_date}:{self.price}"
