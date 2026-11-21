from django.urls import path

from .views import (
    OpportunityListView,
    OpportunityDetailView,
)
from .stage_views import (
    OpportunityStageTransitionView,
    OpportunityStageHistoryView,
)


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
]