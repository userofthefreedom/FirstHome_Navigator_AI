from rest_framework import serializers

from apps.community.models import AgoraComment, AgoraPost


class AgoraCommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = AgoraComment
        fields = "__all__"
        read_only_fields = ("author", "post")

    def get_can_edit(self, obj):
        user = self.context.get("user")
        return bool(user and user.is_authenticated and obj.author_id == user.id)


class AgoraPostSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)
    comments = AgoraCommentSerializer(many=True, read_only=True)
    comment_count = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = AgoraPost
        fields = "__all__"
        read_only_fields = ("author",)

    def get_can_edit(self, obj):
        user = self.context.get("user")
        return bool(user and user.is_authenticated and obj.author_id == user.id)

    def get_comment_count(self, obj):
        return obj.comments.count()
