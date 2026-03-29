"""
Core data models for MoodGallery.

Defines the custom User model and DiaryEntry model with spatial support
for the Geo-Aura Map feature. All emotion analysis (valence, arousal,
dominance) is performed by local AI models — no external APIs.
"""

from django.contrib.gis.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    """Custom user extending AbstractUser with privacy and theme preferences."""

    class ThemeChoice(models.TextChoices):
        DARK = "dark", "Dark"
        LIGHT = "light", "Light"

    is_map_opt_in = models.BooleanField(
        default=False,
        help_text="Allow aggregated emotion data to appear on the global Geo-Aura Map.",
    )
    theme_preference = models.CharField(
        max_length=5,
        choices=ThemeChoice.choices,
        default=ThemeChoice.DARK,
    )

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.username


class DiaryEntry(models.Model):
    """A single diary entry with optional geolocation and AI-generated media.

    Emotion dimensions (valence, arousal, dominance) are extracted by a local
    NLP model and stored as floats in the [-1, 1] range for valence/dominance
    and [0, 1] for arousal.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="diary_entries",
    )
    content = models.TextField(help_text="Raw diary text written by the user.")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Spatial field for Geo-Aura Map clustering (SRID 4326 = WGS 84)
    location = models.PointField(
        spatial_index=True,
        null=True,
        blank=True,
        srid=4326,
        help_text="GPS coordinates where the entry was written.",
    )

    # Paths to locally generated AI assets
    image_path = models.FileField(
        upload_to="diaries/images/",
        null=True,
        blank=True,
        help_text="AI-generated image representing the diary mood.",
    )
    audio_path = models.FileField(
        upload_to="diaries/audio/",
        null=True,
        blank=True,
        help_text="AI-generated ambient audio track for the diary mood.",
    )

    # NLP-extracted emotion dimensions
    valence = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        help_text="Emotional positivity/negativity, range [-1, 1].",
    )
    arousal = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Emotional intensity/energy, range [0, 1].",
    )
    dominance = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        help_text="Sense of control over the emotion, range [-1, 1].",
    )

    class Meta:
        db_table = "diary_entries"
        ordering = ["-created_at"]
        verbose_name_plural = "diary entries"

    def __str__(self):
        return f"DiaryEntry({self.user.username}, {self.created_at:%Y-%m-%d %H:%M})"
