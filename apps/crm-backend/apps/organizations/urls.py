from django.urls import path

from .views import (
    OrganizationListCreateView,
    OrganizationDetailView,
)
from .invitation_views import (
    OrganizationInvitationView,
    RevokeInvitationView,
)

urlpatterns = [
    path(
        "",
        OrganizationListCreateView.as_view(),
        name="organization-list-create",
    ),
    
    path(
        "<uuid:pk>/",
        OrganizationDetailView.as_view(),
        name="organization-detail",
    ),
    
    path(
    "<uuid:organization_id>/invitations/",
    OrganizationInvitationView.as_view(),
    name="organization-invitations",
    ),

    path(
        "<uuid:organization_id>/invitations/<uuid:invitation_id>/revoke/",
        RevokeInvitationView.as_view(),
        name="revoke-invitation",
    ),
]