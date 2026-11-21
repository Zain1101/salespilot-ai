from django.urls import path

from .views import (
    SalesTaskListCreateView,
    SalesTaskDetailView,
    SalesTaskStatusView,
    SalesTaskHistoryView,
)


urlpatterns = [
    path(
        "",
        SalesTaskListCreateView.as_view(),
        name="sales-task-list-create",
    ),
    path(
        "<uuid:pk>/",
        SalesTaskDetailView.as_view(),
        name="sales-task-detail",
    ),
    path(
        "<uuid:pk>/status/",
        SalesTaskStatusView.as_view(),
        name="sales-task-status",
    ),
    path(
        "<uuid:pk>/history/",
        SalesTaskHistoryView.as_view(),
        name="sales-task-history",
    ),
]