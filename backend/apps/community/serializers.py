from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.community.models import AgoraComment, AgoraPost


class AgoraCommentSerializer(serializers.ModelSerializer):
    author_username = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = AgoraComment
        fields = "__all__"
        read_only_fields = ("author", "post")

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_can_edit(self, obj):
        user = self.context.get("user")
        return bool(user and user.is_authenticated and obj.author_id == user.id)

    @extend_schema_field(OpenApiTypes.STR)
    def get_author_username(self, obj):
        return obj.author.first_name or obj.author.username


class AgoraPostSerializer(serializers.ModelSerializer):
    author_username = serializers.SerializerMethodField()
    comments = AgoraCommentSerializer(many=True, read_only=True)
    comment_count = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = AgoraPost
        fields = "__all__"
        read_only_fields = ("author",)

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_can_edit(self, obj):
        user = self.context.get("user")
        return bool(user and user.is_authenticated and obj.author_id == user.id)

    @extend_schema_field(OpenApiTypes.INT)
    def get_comment_count(self, obj):
        return obj.comments.count()

    @extend_schema_field(OpenApiTypes.STR)
    def get_author_username(self, obj):
        return obj.author.first_name or obj.author.username
