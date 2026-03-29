import random
import time

from celery import shared_task
from django.conf import settings


@shared_task(bind=True, name="core.generate_multimodal_diary")
def generate_multimodal_diary_task(self, user_id: int, content: str) -> dict:
    """Mock AI pipeline: sentiment analysis + image/audio generation.

    Simulates ~10 s of GPU inference, then writes random emotion scores
    and dummy asset paths into a new DiaryEntry.
    """
    # --- simulate heavy GPU work ---
    time.sleep(10)

    # --- mock emotion scores ---
    valence = round(random.uniform(-1.0, 1.0), 4)
    arousal = round(random.uniform(0.0, 1.0), 4)
    dominance = round(random.uniform(-1.0, 1.0), 4)

    # --- ensure dummy asset files exist so the frontend won't 404 ---
    images_dir = settings.MEDIA_ROOT / "diaries" / "images"
    audio_dir = settings.MEDIA_ROOT / "diaries" / "audio"
    images_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    mock_image = images_dir / "mock_image.png"
    mock_audio = audio_dir / "mock_audio.mp3"
    if not mock_image.exists():
        mock_image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    if not mock_audio.exists():
        mock_audio.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 64)

    # --- persist to database ---
    from core.models import DiaryEntry  # late import to avoid AppRegistryNotReady

    entry = DiaryEntry.objects.create(
        user_id=user_id,
        content=content,
        valence=valence,
        arousal=arousal,
        dominance=dominance,
        image_path="diaries/images/mock_image.png",
        audio_path="diaries/audio/mock_audio.mp3",
    )

    return {
        "entry_id": entry.id,
        "valence": valence,
        "arousal": arousal,
        "dominance": dominance,
    }
