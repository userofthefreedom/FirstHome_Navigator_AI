from rest_framework import serializers

from apps.products.models import FinancialProduct, LoanProduct


class FinancialProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialProduct
        fields = "__all__"


class LoanProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanProduct
        fields = "__all__"
