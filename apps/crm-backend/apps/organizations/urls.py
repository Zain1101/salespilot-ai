from django.urls import path

from .views import (
    OrganizationListCreateView,
    OrganizationDetailView,
)
from .invitation_views import (
    OrganizationInvitationView,
    RevokeInvitationView,
)
from .member_views import (
    OrganizationMemberListView,
    OrganizationMemberDetailView,
)
from .member_views import UpdateMemberRoleView
from .member_views import (
    DeactivateMemberView,
    ReactivateMemberView,
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
    
    path(
    "<uuid:organization_id>/members/",
    OrganizationMemberListView.as_view(),
    name="organization-members",
    ),

    path(
        "<uuid:organization_id>/members/<uuid:pk>/",
        OrganizationMemberDetailView.as_view(),
        name="organization-member-detail",
    ),
    
    path(
    "<uuid:organization_id>/members/<uuid:member_id>/role/",
    UpdateMemberRoleView.as_view(),
    name="update-member-role",
    ),
    
    path(
    "<uuid:organization_id>/members/<uuid:member_id>/deactivate/",
    DeactivateMemberView.as_view(),
    name="deactivate-member",
    ),

    path(
        "<uuid:organization_id>/members/<uuid:member_id>/reactivate/",
        ReactivateMemberView.as_view(),
        name="reactivate-member",
    ),
]