
from django.urls import path

from .views import OpportunityAIAnalysisView


urlpatterns = [
    path(
        "opportunities/<uuid:pk>/analyze/",
        OpportunityAIAnalysisView.as_view(),
        name="ai-opportunity-analyze",
    ),
]
