from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.mail import send_mail

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from .models import Organization, OrganizationInvitation
from .permissions import IsOrganizationAdmin
from .serializers import (
    InvitationCreateSerializer,
    InvitationSerializer,
)
from .services import create_invitation, accept_invitation
from .serializers import AcceptInvitationSerializer

class OrganizationInvitationView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsOrganizationAdmin,
    ]

    def get_organization(self):
        if not hasattr(self, "_organization"):
            self._organization = get_object_or_404(
                Organization,
                id=self.kwargs["organization_id"],
                is_active=True,
            )
        return self._organization

    def get(self, request, organization_id):
        organization = self.get_organization()

        invitations = (
            OrganizationInvitation.objects
            .filter(organization=organization)
            .select_related("invited_by")
            .order_by("-created_at")
        )

        serializer = InvitationSerializer(
            invitations,
            many=True,
        )

        return Response(serializer.data)

    def post(self, request, organization_id):
        organization = self.get_organization()

        serializer = InvitationCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                invitation, token = create_invitation(
                    organization=organization,
                    invited_by=request.user,
                    email=serializer.validated_data["email"],
                    role=serializer.validated_data["role"],
                )

                # Local development only.
                # The real frontend URL will be configured later.
                invitation_link = (
                    "http://localhost:3000/accept-invitation"
                    f"?token={token}"
                )

                def send_invitation():
                    send_mail(
                        subject=f"Invitation to {organization.name}",
                        message=(
                            f"You have been invited to join "
                            f"{organization.name} on SalesPilot AI.\n\n"
                            f"Accept your invitation:\n"
                            f"{invitation_link}\n\n"
                            f"This invitation expires in 7 days."
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[invitation.email],
                        fail_silently=False,
                    )

                transaction.on_commit(send_invitation)

        except ValidationError as exc:
            return Response(
                {"detail": exc.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            InvitationSerializer(invitation).data,
            status=status.HTTP_201_CREATED,
        )


class RevokeInvitationView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsOrganizationAdmin,
    ]

    def get_organization(self):
        if not hasattr(self, "_organization"):
            self._organization = get_object_or_404(
                Organization,
                id=self.kwargs["organization_id"],
                is_active=True,
            )
        return self._organization

    def post(self, request, organization_id, invitation_id):
        organization = self.get_organization()

        with transaction.atomic():
            invitation = get_object_or_404(
                OrganizationInvitation.objects.select_for_update(),
                id=invitation_id,
                organization=organization,
            )

            if invitation.status != OrganizationInvitation.Status.PENDING:
                return Response(
                    {"detail": "Only pending invitations can be revoked."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            invitation.status = OrganizationInvitation.Status.REVOKED
            invitation.save(update_fields=["status"])

        return Response({
            "message": "Invitation revoked successfully."
        })
        
class AcceptInvitationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AcceptInvitationSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        try:
            membership = accept_invitation(
                token=serializer.validated_data["token"],
                user=request.user,
            )

        except ValidationError as exc:
            return Response(
                {"detail": exc.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "Invitation accepted successfully.",
                "organization": {
                    "id": str(membership.organization.id),
                    "name": membership.organization.name,
                },
                "membership": {
                    "id": str(membership.id),
                    "role": membership.role,
                    "is_active": membership.is_active,
                },
            },
            status=status.HTTP_200_OK,
        )