from django.urls import path

from .views import (
    LeadListCreateView,
    LeadDetailView,
)
from .status_views import (
    LeadStatusTransitionView,
    LeadStatusHistoryView,
)
from .assignment_views import (
    LeadAssignmentView,
    LeadAssignmentHistoryView,
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
    
    path(
    "<uuid:pk>/assign/",
    LeadAssignmentView.as_view(),
    name="lead-assign",
    ),

    path(
        "<uuid:pk>/assignment-history/",
        LeadAssignmentHistoryView.as_view(),
        name="lead-assignment-history",
    ),
]