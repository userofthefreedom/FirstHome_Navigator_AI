from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.community.models import AgoraComment, AgoraPost
from apps.community.serializers import AgoraCommentSerializer, AgoraPostSerializer


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
