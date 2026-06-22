from django.contrib import admin

from apps.market.models import MarketAssetPrice


@admin.register(MarketAssetPrice)
class MarketAssetPriceAdmin(admin.ModelAdmin):
    list_display = ("asset_type", "base_date", "price", "change_rate", "source")
    list_filter = ("asset_type", "source")
    search_fields = ("asset_type",)
