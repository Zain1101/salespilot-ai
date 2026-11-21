from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Organization, Membership
from .permissions import IsOrganizationMember
from .serializers import MembershipSerializer
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsOrganizationAdmin
from .serializers import UpdateMemberRoleSerializer
from .services import update_member_role

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
    
class UpdateMemberRoleView(
    OrganizationMemberMixin,
    APIView,
):
    permission_classes = [
        IsAuthenticated,
        IsOrganizationAdmin,
    ]

    def patch(self, request, organization_id, member_id):
        serializer = UpdateMemberRoleSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        try:
            membership = update_member_role(
                organization=self.get_organization(),
                changed_by=request.user,
                membership_id=member_id,
                new_role=serializer.validated_data["role"],
            )

        except PermissionDenied as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_403_FORBIDDEN,
            )

        except ValidationError as exc:
            return Response(
                {"detail": exc.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            MembershipSerializer(membership).data,
            status=status.HTTP_200_OK,
        )