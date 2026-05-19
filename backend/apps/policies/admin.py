from django.contrib import admin

from apps.policies.models import YouthPolicy


@admin.register(YouthPolicy)
class YouthPolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "policy_category", "age_min", "age_max", "max_income")
    list_filter = ("policy_category", "provider", "requires_homeless")
    search_fields = ("name", "target", "benefit")
