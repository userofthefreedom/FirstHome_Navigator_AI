from rest_framework import serializers

from apps.profiles.models import Favorite, UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "id",
            "name",
            "birth_year",
            "job_status",
            "annual_income",
            "asset",
            "debt",
            "monthly_saving",
            "is_homeless",
            "subscription_months",
            "special_conditions",
            "preferred_regions",
            "preferred_supply_types",
            "target_months",
            "desired_area_min_m2",
            "desired_area_max_m2",
            "desired_price_min",
            "desired_price_max",
            "max_down_payment",
            "monthly_payment_capacity",
        ]


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ["id", "favorite_type", "object_id", "created_at"]
