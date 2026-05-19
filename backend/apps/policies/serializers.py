from rest_framework import serializers

from apps.policies.models import YouthPolicy


class YouthPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = YouthPolicy
        fields = "__all__"
