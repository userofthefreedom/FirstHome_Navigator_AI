from django.contrib import admin

from apps.notices.models import HousingNotice


@admin.register(HousingNotice)
class HousingNoticeAdmin(admin.ModelAdmin):
    list_display = ("title", "provider", "source_id", "region", "supply_type", "price", "application_deadline", "updated_at")
    list_filter = ("provider", "region", "supply_type", "application_deadline")
    search_fields = ("title", "district", "source_id")
    readonly_fields = ("source_meta", "updated_at")
    ordering = ("application_deadline", "id")
