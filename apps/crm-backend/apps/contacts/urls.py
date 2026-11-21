from django.urls import path

from .views import (
    ContactListCreateView,
    ContactDetailView,
)
from .archive_views import (
    ContactArchiveView,
    ContactRestoreView,
)


urlpatterns = [
    path(
        "",
        ContactListCreateView.as_view(),
        name="contact-list-create",
    ),

    path(
        "<uuid:pk>/",
        ContactDetailView.as_view(),
        name="contact-detail",
    ),
    
    path(
    "<uuid:pk>/archive/",
    ContactArchiveView.as_view(),
    name="contact-archive",
    ),

    path(
        "<uuid:pk>/restore/",
        ContactRestoreView.as_view(),
        name="contact-restore",
    ),
]