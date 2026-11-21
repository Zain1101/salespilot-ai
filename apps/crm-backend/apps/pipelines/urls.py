from django.urls import path

from .views import (
    PipelineListCreateView,
    PipelineDetailView,
)


urlpatterns = [
    path(
        "",
        PipelineListCreateView.as_view(),
        name="pipeline-list-create",
    ),

    path(
        "<uuid:pk>/",
        PipelineDetailView.as_view(),
        name="pipeline-detail",
    ),
]