
from django.urls import path

from .views import (
    OpportunityAIAnalysisView,
    SalesAgentView,
)


urlpatterns = [
    path(
        "opportunities/<uuid:pk>/analyze/",
        OpportunityAIAnalysisView.as_view(),
        name="ai-opportunity-analyze",
    ),

    path(
        "agent/",
        SalesAgentView.as_view(),
        name="ai-sales-agent",
    ),
]
