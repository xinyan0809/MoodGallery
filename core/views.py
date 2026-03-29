from datetime import timedelta

from celery.result import AsyncResult
from django.contrib.gis.geos import Polygon
from django.db.models import Avg
from django.db.models.functions import TruncDay
from django.utils import timezone
from django_filters import rest_framework as df_filters
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import DiaryEntry
from core.tasks import generate_multimodal_diary_task


# ---------------------------------------------------------------------------
# Async generation
# ---------------------------------------------------------------------------


class DiaryEntryGenerateView(APIView):
    """Accept diary text and kick off the async AI generation pipeline."""

    permission_classes = [IsAuthenticated]

    class InputSerializer(serializers.Serializer):
        content = serializers.CharField(min_length=1)

    def post(self, request):
        ser = self.InputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        task = generate_multimodal_diary_task.delay(
            user_id=request.user.id,
            content=ser.validated_data["content"],
        )

        return Response(
            {"task_id": task.id, "status": "processing"},
            status=status.HTTP_202_ACCEPTED,
        )


class TaskStatusView(APIView):
    """Poll the status of a Celery task by its ID."""

    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        result = AsyncResult(task_id)

        payload = {"task_id": task_id, "status": result.status}

        if result.successful():
            payload["result"] = result.result
        elif result.failed():
            payload["error"] = str(result.result)

        return Response(payload)


# ---------------------------------------------------------------------------
# Diary archive (list with filtering + pagination)
# ---------------------------------------------------------------------------


class DiaryEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = DiaryEntry
        fields = [
            "id",
            "content",
            "created_at",
            "valence",
            "arousal",
            "dominance",
            "image_path",
            "audio_path",
        ]


class DiaryEntryFilter(df_filters.FilterSet):
    created_after = df_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_before = df_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )
    valence_min = df_filters.NumberFilter(field_name="valence", lookup_expr="gte")
    valence_max = df_filters.NumberFilter(field_name="valence", lookup_expr="lte")
    arousal_min = df_filters.NumberFilter(field_name="arousal", lookup_expr="gte")
    arousal_max = df_filters.NumberFilter(field_name="arousal", lookup_expr="lte")
    dominance_min = df_filters.NumberFilter(field_name="dominance", lookup_expr="gte")
    dominance_max = df_filters.NumberFilter(field_name="dominance", lookup_expr="lte")

    class Meta:
        model = DiaryEntry
        fields: list[str] = []


class DiaryEntryListView(generics.ListAPIView):
    """Paginated, filterable diary archive for the authenticated user."""

    permission_classes = [IsAuthenticated]
    serializer_class = DiaryEntrySerializer
    filterset_class = DiaryEntryFilter

    def get_queryset(self):
        return DiaryEntry.objects.filter(user=self.request.user)


# ---------------------------------------------------------------------------
# Insights — 30-day daily aggregation of VAD scores
# ---------------------------------------------------------------------------


class InsightsView(APIView):
    """Return daily average valence / arousal / dominance over the last 30 days.

    The aggregation uses TruncDay + Avg pushed down to PostgreSQL, so only
    one lightweight query is executed regardless of how many diary entries
    exist in the window.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        since = timezone.now() - timedelta(days=30)

        rows = (
            DiaryEntry.objects.filter(user=request.user, created_at__gte=since)
            .annotate(day=TruncDay("created_at"))
            .values("day")
            .annotate(
                avg_valence=Avg("valence"),
                avg_arousal=Avg("arousal"),
                avg_dominance=Avg("dominance"),
            )
            .order_by("day")
        )

        data = [
            {
                "date": row["day"].date().isoformat(),
                "valence": round(row["avg_valence"], 4) if row["avg_valence"] is not None else None,
                "arousal": round(row["avg_arousal"], 4) if row["avg_arousal"] is not None else None,
                "dominance": round(row["avg_dominance"], 4) if row["avg_dominance"] is not None else None,
            }
            for row in rows
        ]

        return Response(data)


# ---------------------------------------------------------------------------
# Geo-Aura Map — privacy-safe, spatially filtered emotion heatmap
# ---------------------------------------------------------------------------


class GlobalMapView(APIView):
    """Public heatmap endpoint returning anonymised VAD scores with locations.

    Privacy: only includes entries from users who opted in (is_map_opt_in=True).
    Never exposes content, asset paths, or user identifiers.

    Spatial filtering: accepts ``?in_bbox=min_lon,min_lat,max_lon,max_lat``
    and builds a PostGIS ST_Within / ST_Intersects query via a GEOS Polygon
    constructed from the bounding box.  The spatial_index on ``location``
    keeps this fast even with millions of rows.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        qs = DiaryEntry.objects.filter(
            user__is_map_opt_in=True,
            location__isnull=False,
        ).select_related(None)  # no joins beyond the user FK filter

        bbox_param = request.query_params.get("in_bbox")
        if bbox_param:
            try:
                coords = [float(c) for c in bbox_param.split(",")]
                if len(coords) != 4:
                    raise ValueError
                min_lon, min_lat, max_lon, max_lat = coords
            except (ValueError, TypeError):
                return Response(
                    {"detail": "in_bbox must be 4 comma-separated floats: min_lon,min_lat,max_lon,max_lat"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            bbox_poly = Polygon.from_bbox((min_lon, min_lat, max_lon, max_lat))
            bbox_poly.srid = 4326
            qs = qs.filter(location__within=bbox_poly)

        # Only expose coordinates + VAD — never content, paths, or user info.
        points = qs.values_list(
            "location", "valence", "arousal", "dominance"
        )

        data = [
            {
                "lng": pt.x,
                "lat": pt.y,
                "valence": v,
                "arousal": a,
                "dominance": d,
            }
            for pt, v, a, d in points
            if pt is not None
        ]

        return Response(data)
