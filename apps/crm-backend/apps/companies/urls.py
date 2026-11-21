from django.urls import path

from .views import (
    CompanyListCreateView,
    CompanyDetailView,
)

from apps.contacts.archive_views import (
    CompanyArchiveView,
    CompanyRestoreView,
)


urlpatterns = [
    path(
        "",
        CompanyListCreateView.as_view(),
        name="company-list-create",
    ),

    path(
        "<uuid:pk>/",
        CompanyDetailView.as_view(),
        name="company-detail",
    ),
    path(
    "<uuid:pk>/archive/",
    CompanyArchiveView.as_view(),
    name="company-archive",
    ),

    path(
        "<uuid:pk>/restore/",
        CompanyRestoreView.as_view(),
        name="company-restore",
    ),
]