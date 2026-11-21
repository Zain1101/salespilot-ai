from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Organization, Membership
from .permissions import IsOrganizationMember
from .serializers import MembershipSerializer


class OrganizationMemberMixin:
    """
    Shared organization lookup and membership
    filtering for team management endpoints.
    """

    def get_organization(self):

        if not hasattr(self, "_organization"):

            self._organization = get_object_or_404(
                Organization,
                id=self.kwargs["organization_id"],
                is_active=True,
            )

        return self._organization

    def get_queryset(self):

        organization = self.get_organization()

        return (
            Membership.objects
            .filter(
                organization=organization,
                is_active=True,
                user__is_active=True,
            )
            .select_related("user", "organization")
            .order_by("user__email")
        )


class OrganizationMemberListView(
    OrganizationMemberMixin,
    generics.ListAPIView,
):

    serializer_class = MembershipSerializer

    permission_classes = [
        IsAuthenticated,
        IsOrganizationMember,
    ]


class OrganizationMemberDetailView(
    OrganizationMemberMixin,
    generics.RetrieveAPIView,
):

    serializer_class = MembershipSerializer

    permission_classes = [
        IsAuthenticated,
        IsOrganizationMember,
    ]