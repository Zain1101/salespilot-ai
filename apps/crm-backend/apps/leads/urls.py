from django.urls import path

from .views import (
    LeadListCreateView,
    LeadDetailView,
)
from .status_views import (
    LeadStatusTransitionView,
    LeadStatusHistoryView,
)


urlpatterns = [
    path(
        "",
        LeadListCreateView.as_view(),
        name="lead-list-create",
    ),

    path(
        "<uuid:pk>/",
        LeadDetailView.as_view(),
        name="lead-detail",
    ),
    
    path(
    "<uuid:pk>/transition/",
    LeadStatusTransitionView.as_view(),
    name="lead-transition",
    ),

    path(
        "<uuid:pk>/status-history/",
        LeadStatusHistoryView.as_view(),
        name="lead-status-history",
    ),
]