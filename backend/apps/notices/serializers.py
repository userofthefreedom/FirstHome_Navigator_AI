from rest_framework import serializers

from apps.notices.models import HousingNotice


class HousingNoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HousingNotice
        fields = "__all__"
