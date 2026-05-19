from django.contrib import admin

from apps.notices.models import HousingNotice


@admin.register(HousingNotice)
class HousingNoticeAdmin(admin.ModelAdmin):
    list_display = ("title", "provider", "region", "supply_type", "price", "application_deadline")
    list_filter = ("region", "supply_type", "provider")
    search_fields = ("title", "district")
