from rest_framework import serializers

from apps.products.models import FinancialProduct


class FinancialProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialProduct
        fields = "__all__"
