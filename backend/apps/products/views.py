import re

from django.db.models import Max, Prefetch, Q
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.fixture_store import products as fixture_products
from apps.products.models import FinancialProduct, FinancialProductOption, UserJoinedProduct
from apps.products.serializers import FinancialProductSerializer, UserJoinedProductSerializer
from apps.products.services.matcher import match_products
from apps.profiles.services import profile_from_request


def _product_queryset():
    return FinancialProduct.objects.prefetch_related(
        Prefetch("options", queryset=FinancialProductOption.objects.order_by("save_trm", "-intr_rate2"))
    ).annotate(best_rate=Max("options__intr_rate2"))


def _category_label(value: str) -> str:
    return {"deposit": "정기예금", "saving": "적금", "예금": "정기예금", "적금": "적금"}.get(value, value)


def _normalize_category(value: str) -> str:
    aliases = {
        "": "",
        "all": "",
        "deposit": "예금",
        "saving": "적금",
        "정기예금": "예금",
        "예금": "예금",
        "적금": "적금",
    }
    return aliases.get(str(value or "").strip(), str(value or "").strip())


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
    category = _normalize_category(request.query_params.get("category", "all"))
    provider = request.query_params.get("provider", "")
    query = request.query_params.get("q", "")
    term_months = request.query_params.get("term_months", "")
    ordering = request.query_params.get("ordering", "fit")

    if category:
        queryset = queryset.filter(category=category)
    if provider:
        queryset = queryset.filter(provider=provider)
    if query:
        queryset = queryset.filter(Q(name__icontains=query) | Q(provider__icontains=query))
    if term_months:
        months = int(term_months)
        queryset = queryset.filter(Q(term_months=months) | Q(options__save_trm=months)).distinct()

    if not FinancialProduct.objects.exists():
        items = _fixture_items()
        providers = sorted({item["provider"] for item in items if item.get("provider")})
        categories = sorted({item["category"] for item in items if item.get("category")})
        return Response({"items": items, "filters": {"providers": providers, "categories": categories}})

    serializer = FinancialProductSerializer(queryset, many=True, context={"user": request.user})
    all_products = FinancialProduct.objects.all()
    providers = list(all_products.order_by("provider").values_list("provider", flat=True).distinct())
    categories = list(all_products.order_by("category").values_list("category", flat=True).distinct())
    match_rank, match_scores = _product_match_maps(request)
    items = [_decorate_product_item(item, match_rank, match_scores) for item in serializer.data]
    items = _sort_product_items(items, ordering, match_rank)
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
    match_rank, match_scores = _product_match_maps(request)
    data = _decorate_product_item(data, match_rank, match_scores)
    data["options"] = _product_options_or_single_term(data)
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


@api_view(["DELETE"])
def joined_product_detail_view(request, joined_id: int):
    if not request.user.is_authenticated:
        return Response({"detail": "login required"}, status=401)
    deleted_count, _ = UserJoinedProduct.objects.filter(id=joined_id, user=request.user).delete()
    if not deleted_count:
        return Response({"detail": "joined product not found"}, status=404)
    return Response(status=204)


def _product_match_maps(request) -> tuple[dict[int, int], dict[int, int]]:
    try:
        matched = match_products(profile_from_request(request), limit=1000)
    except Exception:
        matched = []
    rank = {int(item["id"]): index for index, item in enumerate(matched) if item.get("id") is not None}
    scores = {int(item["id"]): int(item.get("match_score") or 0) for item in matched if item.get("id") is not None}
    return rank, scores


def _decorate_product_item(item: dict, match_rank: dict[int, int], match_scores: dict[int, int]) -> dict:
    product_id = int(item.get("id") or 0)
    best_option = item.get("best_option")
    best_option_term = int(best_option.get("save_trm") or 0) if isinstance(best_option, dict) else 0
    term_months = int(item.get("term_months") or best_option_term or 0)
    option_count = int(item.get("option_count") or 0)
    if option_count == 0 and term_months:
        option_count = 1
    return {
        **item,
        "term_months": term_months,
        "option_count": option_count,
        "category_label": _category_label(item.get("category", "")),
        "match_score": match_scores.get(product_id, 0),
        "fit_rank": match_rank.get(product_id),
    }


def _product_options_or_single_term(item: dict) -> list[dict]:
    options = list(item.get("options") or [])
    if options:
        return options
    term_months = int(item.get("term_months") or 0)
    if not term_months:
        return []
    rate = _rate_number(item)
    return [
        {
            "id": None,
            "save_trm": term_months,
            "intr_rate": rate,
            "intr_rate2": rate,
            "intr_rate_type_nm": "대표 금리",
            "synthetic": True,
        }
    ]


def _sort_product_items(items: list[dict], ordering: str, match_rank: dict[int, int]) -> list[dict]:
    if ordering == "rate":
        return sorted(items, key=lambda item: (-_rate_number(item), item.get("provider") or "", item.get("name") or ""))
    if ordering == "term":
        return sorted(items, key=lambda item: (int(item.get("term_months") or 9999), -_rate_number(item), item.get("provider") or "", item.get("name") or ""))
    if ordering == "provider":
        return sorted(items, key=lambda item: (item.get("provider") or "", item.get("name") or ""))
    if ordering == "name":
        return sorted(items, key=lambda item: (item.get("name") or "", item.get("provider") or ""))
    return sorted(
        items,
        key=lambda item: (
            match_rank.get(int(item.get("id") or 0), 10_000),
            -int(item.get("match_score") or 0),
            -_rate_number(item),
            item.get("provider") or "",
            item.get("name") or "",
        ),
    )


def _rate_number(item: dict) -> float:
    candidates = []
    best_option = item.get("best_option")
    if isinstance(best_option, dict):
        candidates.extend([best_option.get("intr_rate2"), best_option.get("intr_rate")])
    candidates.append(item.get("rate"))
    for value in candidates:
        match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
        if match:
            return float(match.group(0))
    return 0.0
