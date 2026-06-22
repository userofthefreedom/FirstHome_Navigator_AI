from django.contrib import admin

from apps.community.models import AgoraComment, AgoraPost


class AgoraCommentInline(admin.TabularInline):
    model = AgoraComment
    extra = 0


@admin.register(AgoraPost)
class AgoraPostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "created_at", "updated_at")
    list_filter = ("category", "created_at")
    search_fields = ("title", "content", "author__username")
    inlines = [AgoraCommentInline]


@admin.register(AgoraComment)
class AgoraCommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "created_at", "updated_at")
    search_fields = ("content", "author__username", "post__title")
