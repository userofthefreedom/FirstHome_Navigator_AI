from django.contrib import admin

from apps.products.models import FinancialProduct, LoanProduct


@admin.register(FinancialProduct)
class FinancialProductAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "category", "rate", "term_months", "monthly_limit", "protection_status", "updated_at")
    list_filter = ("category", "protection_status", "provider", "term_months")
    search_fields = ("name", "provider")
    ordering = ("term_months", "provider", "name")


@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "category", "loan_purpose", "rate", "limit_amount", "updated_at")
    list_filter = ("category", "loan_purpose", "provider", "requires_homeless")
    search_fields = ("name", "provider", "description", "target")
    ordering = ("provider", "name")
