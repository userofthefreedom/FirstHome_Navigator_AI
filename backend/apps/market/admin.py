from django.contrib import admin

from apps.market.models import MarketAssetPrice


@admin.register(MarketAssetPrice)
class MarketAssetPriceAdmin(admin.ModelAdmin):
    list_display = ("asset_type", "base_date", "region_name", "price", "change_rate", "source")
    list_filter = ("asset_type", "source", "region_name")
    search_fields = ("asset_type", "region_name", "region_code")
