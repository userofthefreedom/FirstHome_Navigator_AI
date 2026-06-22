from django.db.models import Max, Prefetch, Q
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.fixture_store import products as fixture_products
from apps.products.models import FinancialProduct, FinancialProductOption, UserJoinedProduct
from apps.products.serializers import FinancialProductSerializer, UserJoinedProductSerializer


def _product_queryset():
    return FinancialProduct.objects.prefetch_related(
        Prefetch("options", queryset=FinancialProductOption.objects.order_by("save_trm", "-intr_rate2"))
    ).annotate(best_rate=Max("options__intr_rate2"))


def _category_label(value: str) -> str:
    return {"deposit": "정기예금", "saving": "적금", "예금": "정기예금"}.get(value, value)


def _fixture_items():
    items = []
    for product in fixture_products():
        items.append(
            {
                **product,
                "best_option": None,
                "option_count": 0,
                "joined": False,
                "category_label": _category_label(str(product.get("category", ""))),
            }
        )
    return items


@api_view(["GET"])
def products_view(request):
    queryset = _product_queryset()
    category = request.query_params.get("category", "all")
    provider = request.query_params.get("provider", "")
    query = request.query_params.get("q", "")
    term_months = request.query_params.get("term_months", "")
    ordering = request.query_params.get("ordering", "fit")

    if category and category != "all":
        queryset = queryset.filter(category=category)
    if provider:
        queryset = queryset.filter(provider=provider)
    if query:
        queryset = queryset.filter(Q(name__icontains=query) | Q(provider__icontains=query))
    if term_months:
        queryset = queryset.filter(options__save_trm=int(term_months)).distinct()

    orderings = {
        "rate": ("-best_rate", "-rate", "provider", "name"),
        "term": ("term_months", "-best_rate", "provider", "name"),
        "provider": ("provider", "name"),
        "name": ("name",),
        "fit": ("-best_rate", "term_months", "provider", "name"),
    }
    queryset = queryset.order_by(*orderings.get(ordering, orderings["fit"]))

    if not FinancialProduct.objects.exists():
        items = _fixture_items()
        providers = sorted({item["provider"] for item in items if item.get("provider")})
        categories = sorted({item["category"] for item in items if item.get("category")})
        return Response({"items": items, "filters": {"providers": providers, "categories": categories}})

    serializer = FinancialProductSerializer(queryset, many=True, context={"user": request.user})
    all_products = FinancialProduct.objects.all()
    providers = list(all_products.order_by("provider").values_list("provider", flat=True).distinct())
    categories = list(all_products.order_by("category").values_list("category", flat=True).distinct())
    items = [
        {
            **item,
            "category_label": _category_label(item.get("category", "")),
            "match_score": None,
        }
        for item in serializer.data
    ]
    return Response({"items": items, "filters": {"providers": providers, "categories": categories}})


@api_view(["GET"])
def product_detail_view(request, product_id: int):
    try:
        product = _product_queryset().get(id=product_id)
    except FinancialProduct.DoesNotExist:
        fixture = next((item for item in _fixture_items() if int(item.get("id", 0)) == product_id), None)
        if fixture:
            return Response(fixture)
        return Response({"detail": "product not found"}, status=404)
    data = FinancialProductSerializer(product, context={"user": request.user}).data
    data["category_label"] = _category_label(data.get("category", ""))
    data["caveats"] = [
        "금리와 가입 조건은 금융회사 공시 변경에 따라 달라질 수 있습니다.",
        "가입 전 금융회사 공식 상품 설명서와 우대조건을 확인해야 합니다.",
    ]
    return Response(data)


@api_view(["POST"])
def join_product_view(request, product_id: int):
    if not request.user.is_authenticated:
        return Response({"detail": "login required"}, status=401)
    try:
        product = FinancialProduct.objects.get(id=product_id)
    except FinancialProduct.DoesNotExist:
        return Response({"detail": "product not found"}, status=404)

    option_id = request.data.get("option_id")
    selected_option = None
    if option_id:
        selected_option = FinancialProductOption.objects.filter(id=option_id, product=product).first()
        if selected_option is None:
            return Response({"detail": "option not found"}, status=400)
    joined, _created = UserJoinedProduct.objects.update_or_create(
        user=request.user,
        product=product,
        defaults={
            "selected_option": selected_option,
            "memo": str(request.data.get("memo", ""))[:200],
        },
    )
    return Response(UserJoinedProductSerializer(joined, context={"user": request.user}).data, status=201)


@api_view(["GET"])
def joined_products_view(request):
    if not request.user.is_authenticated:
        return Response({"detail": "login required"}, status=401)
    joined = UserJoinedProduct.objects.filter(user=request.user).select_related("product", "selected_option").prefetch_related("product__options")
    return Response(UserJoinedProductSerializer(joined, many=True, context={"user": request.user}).data)
