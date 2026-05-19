from django.contrib import admin

from apps.policies.models import YouthPolicy


@admin.register(YouthPolicy)
class YouthPolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "policy_category", "age_min", "age_max", "max_income", "requires_homeless", "updated_at")
    list_filter = ("policy_category", "provider", "requires_homeless", "age_min", "age_max")
    search_fields = ("name", "target", "benefit")
    ordering = ("policy_category", "provider", "name")
