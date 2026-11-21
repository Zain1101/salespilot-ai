from django.urls import path

from .views import SalesOverviewView


urlpatterns = [
    path(
        "overview/",
        SalesOverviewView.as_view(),
        name="analytics-overview",
    ),
]