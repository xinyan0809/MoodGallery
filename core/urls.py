from django.urls import path

from core.views import (
    DiaryEntryGenerateView,
    DiaryEntryListView,
    GlobalMapView,
    InsightsView,
    TaskStatusView,
)

app_name = "core"

urlpatterns = [
    path("diary/generate/", DiaryEntryGenerateView.as_view(), name="diary-generate"),
    path("diary/", DiaryEntryListView.as_view(), name="diary-list"),
    path("insights/", InsightsView.as_view(), name="insights"),
    path("map/", GlobalMapView.as_view(), name="global-map"),
    path("tasks/<str:task_id>/", TaskStatusView.as_view(), name="task-status"),
]
