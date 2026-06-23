from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.api_schema import COMMON_ERROR_RESPONSES, MODEL_RESPONSES, TAGS
from apps.community.models import AgoraComment, AgoraPost
from apps.community.serializers import AgoraCommentSerializer, AgoraPostSerializer


@extend_schema(
    methods=["GET"],
    tags=[TAGS["community"]],
    summary="청약 아고라 게시글 목록",
    description="게시판 카테고리와 검색어 기준으로 청약 아고라 게시글을 최대 50개 반환합니다.",
    parameters=[
        OpenApiParameter("category", str, OpenApiParameter.QUERY, description="notice, product, funding, free"),
        OpenApiParameter("q", str, OpenApiParameter.QUERY, description="제목 검색어"),
    ],
    responses={200: MODEL_RESPONSES["post"](many=True)},
)
@extend_schema(
    methods=["POST"],
    tags=[TAGS["community"]],
    summary="청약 아고라 게시글 작성",
    description="로그인 사용자가 게시글을 작성합니다.",
    request=MODEL_RESPONSES["post"],
    responses={201: MODEL_RESPONSES["post"], **COMMON_ERROR_RESPONSES},
)
@api_view(["GET", "POST"])
def posts_view(request):
    if request.method == "GET":
        queryset = AgoraPost.objects.select_related("author").prefetch_related("comments__author")
        category = request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)
        query = request.query_params.get("q", "")
        if query:
            queryset = queryset.filter(title__icontains=query)
        return Response(AgoraPostSerializer(queryset[:50], many=True, context={"user": request.user}).data)

    if not request.user.is_authenticated:
        return Response({"detail": "login required"}, status=401)
    serializer = AgoraPostSerializer(data=request.data, context={"user": request.user})
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    post = serializer.save(author=request.user)
    return Response(AgoraPostSerializer(post, context={"user": request.user}).data, status=201)


@extend_schema(
    methods=["GET"],
    tags=[TAGS["community"]],
    summary="청약 아고라 게시글 상세",
    description="댓글을 포함한 게시글 상세 정보를 반환합니다.",
    responses={200: MODEL_RESPONSES["post"], **COMMON_ERROR_RESPONSES},
)
@extend_schema(
    methods=["PUT"],
    tags=[TAGS["community"]],
    summary="청약 아고라 게시글 수정",
    description="작성자 본인만 게시글을 수정할 수 있습니다.",
    request=MODEL_RESPONSES["post"],
    responses={200: MODEL_RESPONSES["post"], **COMMON_ERROR_RESPONSES},
)
@extend_schema(
    methods=["DELETE"],
    tags=[TAGS["community"]],
    summary="청약 아고라 게시글 삭제",
    description="작성자 본인만 게시글을 삭제할 수 있습니다.",
    responses={204: None, **COMMON_ERROR_RESPONSES},
)
@api_view(["GET", "PUT", "DELETE"])
def post_detail_view(request, post_id: int):
    try:
        post = AgoraPost.objects.select_related("author").prefetch_related("comments__author").get(id=post_id)
    except AgoraPost.DoesNotExist:
        return Response({"detail": "post not found"}, status=404)
    if request.method == "GET":
        return Response(AgoraPostSerializer(post, context={"user": request.user}).data)
    if not request.user.is_authenticated or post.author_id != request.user.id:
        return Response({"detail": "permission denied"}, status=403)
    if request.method == "DELETE":
        post.delete()
        return Response(status=204)
    serializer = AgoraPostSerializer(post, data=request.data, partial=True, context={"user": request.user})
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    return Response(AgoraPostSerializer(serializer.save(), context={"user": request.user}).data)


@extend_schema(
    tags=[TAGS["community"]],
    summary="청약 아고라 댓글 작성",
    description="로그인 사용자가 특정 게시글에 댓글을 작성합니다.",
    request=MODEL_RESPONSES["comment"],
    responses={201: MODEL_RESPONSES["comment"], **COMMON_ERROR_RESPONSES},
)
@api_view(["POST"])
def comments_view(request, post_id: int):
    if not request.user.is_authenticated:
        return Response({"detail": "login required"}, status=401)
    try:
        post = AgoraPost.objects.get(id=post_id)
    except AgoraPost.DoesNotExist:
        return Response({"detail": "post not found"}, status=404)
    serializer = AgoraCommentSerializer(data=request.data, context={"user": request.user})
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    comment = serializer.save(author=request.user, post=post)
    return Response(AgoraCommentSerializer(comment, context={"user": request.user}).data, status=201)


@extend_schema(
    methods=["PUT"],
    tags=[TAGS["community"]],
    summary="청약 아고라 댓글 수정",
    description="작성자 본인만 댓글을 수정할 수 있습니다.",
    request=MODEL_RESPONSES["comment"],
    responses={200: MODEL_RESPONSES["comment"], **COMMON_ERROR_RESPONSES},
)
@extend_schema(
    methods=["DELETE"],
    tags=[TAGS["community"]],
    summary="청약 아고라 댓글 삭제",
    description="작성자 본인만 댓글을 삭제할 수 있습니다.",
    responses={204: None, **COMMON_ERROR_RESPONSES},
)
@api_view(["PUT", "DELETE"])
def comment_detail_view(request, comment_id: int):
    try:
        comment = AgoraComment.objects.select_related("author").get(id=comment_id)
    except AgoraComment.DoesNotExist:
        return Response({"detail": "comment not found"}, status=404)
    if not request.user.is_authenticated or comment.author_id != request.user.id:
        return Response({"detail": "permission denied"}, status=403)
    if request.method == "DELETE":
        comment.delete()
        return Response(status=204)
    serializer = AgoraCommentSerializer(comment, data=request.data, partial=True, context={"user": request.user})
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    return Response(AgoraCommentSerializer(serializer.save(), context={"user": request.user}).data)
