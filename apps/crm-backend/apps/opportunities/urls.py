from django.urls import path

from .views import (
    OpportunityListView,
    OpportunityDetailView,
)
from .stage_views import (
    OpportunityStageTransitionView,
    OpportunityStageHistoryView,
)
from .outcome_views import (
    OpportunityCloseView,
    OpportunityOutcomeHistoryView,
)
from .timeline_views import OpportunityTimelineView


urlpatterns = [
    path(
        "",
        OpportunityListView.as_view(),
        name="opportunity-list",
    ),

    path(
        "<uuid:pk>/",
        OpportunityDetailView.as_view(),
        name="opportunity-detail",
    ),
    
    path(
    "<uuid:pk>/move-stage/",
    OpportunityStageTransitionView.as_view(),
    name="opportunity-move-stage",
    ),

    path(
        "<uuid:pk>/stage-history/",
        OpportunityStageHistoryView.as_view(),
        name="opportunity-stage-history",
    ),
    
    path(
    "<uuid:pk>/close/",
    OpportunityCloseView.as_view(),
    name="opportunity-close",
    ),

    path(
        "<uuid:pk>/outcome-history/",
        OpportunityOutcomeHistoryView.as_view(),
        name="opportunity-outcome-history",
    ),
    
    path(
    "<uuid:pk>/timeline/",
    OpportunityTimelineView.as_view(),
    name="opportunity-timeline",
    ),
]