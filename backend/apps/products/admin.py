from django.contrib import admin

from apps.products.models import FinancialProduct


@admin.register(FinancialProduct)
class FinancialProductAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "category", "term_months", "monthly_limit", "protection_status")
    list_filter = ("category", "protection_status", "provider")
    search_fields = ("name", "provider")
