from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.products.models import FinancialProduct, FinancialProductOption, LoanProduct, UserJoinedProduct


class FinancialProductOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialProductOption
        fields = "__all__"


class FinancialProductSerializer(serializers.ModelSerializer):
    options = FinancialProductOptionSerializer(many=True, read_only=True)
    best_option = serializers.SerializerMethodField()
    option_count = serializers.SerializerMethodField()
    joined = serializers.SerializerMethodField()

    class Meta:
        model = FinancialProduct
        fields = "__all__"

    @extend_schema_field(FinancialProductOptionSerializer)
    def get_best_option(self, obj):
        option = max(obj.options.all(), key=lambda item: (item.intr_rate2, item.intr_rate, item.save_trm), default=None)
        return FinancialProductOptionSerializer(option).data if option else None

    @extend_schema_field(OpenApiTypes.INT)
    def get_option_count(self, obj):
        return len(getattr(obj, "_prefetched_objects_cache", {}).get("options", [])) or obj.options.count()

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_joined(self, obj):
        user = self.context.get("user")
        if not user or not user.is_authenticated:
            return False
        return UserJoinedProduct.objects.filter(user=user, product=obj).exists()


class UserJoinedProductSerializer(serializers.ModelSerializer):
    product = FinancialProductSerializer(read_only=True)
    selected_option = FinancialProductOptionSerializer(read_only=True)

    class Meta:
        model = UserJoinedProduct
        fields = "__all__"


class LoanProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanProduct
        fields = "__all__"
