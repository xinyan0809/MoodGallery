"""DRF serializers for MoodGallery core models."""

from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import User, DiaryEntry


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile data (excludes sensitive auth fields)."""

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "is_map_opt_in",
            "theme_preference",
            "date_joined",
        )
        read_only_fields = ("id", "username", "date_joined")


class DiaryEntrySerializer(GeoFeatureModelSerializer):
    """GeoJSON-compatible serializer for diary entries.

    Outputs each entry as a GeoJSON Feature with the location as the
    geometry and all other fields as properties. This makes the response
    directly consumable by mapping libraries (Leaflet, Mapbox GL, etc.).
    """

    user = serializers.ReadOnlyField(source="user.username")

    class Meta:
        model = DiaryEntry
        geo_field = "location"
        fields = (
            "id",
            "user",
            "content",
            "created_at",
            "image_path",
            "audio_path",
            "valence",
            "arousal",
            "dominance",
        )
        read_only_fields = ("id", "user", "created_at")


class DiaryEntryCreateSerializer(serializers.ModelSerializer):
    """Flat serializer used for creating/updating diary entries.

    Accepts location as a GeoJSON geometry object:
    {"type": "Point", "coordinates": [longitude, latitude]}
    """

    class Meta:
        model = DiaryEntry
        fields = (
            "id",
            "content",
            "location",
            "image_path",
            "audio_path",
            "valence",
            "arousal",
            "dominance",
            "created_at",
        )
        read_only_fields = ("id", "created_at", "image_path", "audio_path", "valence", "arousal", "dominance")
