"""Admin configuration for MoodGallery core models."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.gis.admin import GISModelAdmin

from .models import User, DiaryEntry


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin view for the custom User model."""

    list_display = (
        "username",
        "email",
        "is_map_opt_in",
        "theme_preference",
        "is_staff",
    )
    list_filter = BaseUserAdmin.list_filter + ("is_map_opt_in", "theme_preference")
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "MoodGallery Preferences",
            {"fields": ("is_map_opt_in", "theme_preference")},
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "MoodGallery Preferences",
            {"fields": ("is_map_opt_in", "theme_preference")},
        ),
    )


@admin.register(DiaryEntry)
class DiaryEntryAdmin(GISModelAdmin):
    """Admin view for DiaryEntry with map widget for the location field."""

    list_display = ("user", "created_at", "valence", "arousal", "dominance", "has_location")
    list_filter = ("created_at", "user")
    search_fields = ("content", "user__username")
    readonly_fields = ("created_at",)
    raw_id_fields = ("user",)

    @admin.display(boolean=True, description="Has Location")
    def has_location(self, obj):
        return obj.location is not None
