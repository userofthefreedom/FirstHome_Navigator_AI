from django.contrib import admin

from apps.profiles.models import Favorite, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "birth_year", "annual_income", "asset", "monthly_saving", "updated_at")
    search_fields = ("name", "user__username", "user__email")


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "client_id", "favorite_type", "object_id", "created_at")
    list_filter = ("favorite_type", "user")
    search_fields = ("user__username", "client_id")
