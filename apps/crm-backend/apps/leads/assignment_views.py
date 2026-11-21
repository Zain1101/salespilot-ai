from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.tenancy.permissions import (
    IsTenantMember,
    IsTenantEditor,
)

from .models import Lead, LeadAssignmentHistory
from .serializers import (
    LeadSerializer,
    LeadAssignmentSerializer,
)
from .services import assign_lead


class LeadAssignmentView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTenantEditor,
    ]

    def post(self, request, organization_id, pk):

        serializer = LeadAssignmentSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        try:
            lead = assign_lead(
                organization_id=organization_id,
                lead_id=pk,
                changed_by=request.user,
                assignee_id=serializer.validated_data[
                    "assigned_to"
                ],
                reason=serializer.validated_data.get(
                    "reason", ""
                ),
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
            LeadSerializer(
                lead,
                context={
                    "request": request,
                    "view": self,
                },
            ).data,
            status=status.HTTP_200_OK,
        )


class LeadAssignmentHistoryView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]

    def get(self, request, organization_id, pk):

        lead = Lead.objects.filter(
            pk=pk,
            organization_id=organization_id,
        ).first()

        if lead is None:
            return Response(
                {"detail": "Lead not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        history = (
            LeadAssignmentHistory.objects
            .filter(
                organization_id=organization_id,
                lead=lead,
            )
            .select_related(
                "previous_assignee__user",
                "new_assignee__user",
                "changed_by",
            )
            .order_by("-created_at", "-id")
        )

        return Response([
            {
                "id": str(event.id),
                "previous_assignee": (
                    str(event.previous_assignee_id)
                    if event.previous_assignee_id
                    else None
                ),
                "previous_assignee_email": (
                    event.previous_assignee.user.email
                    if event.previous_assignee
                    else None
                ),
                "new_assignee": (
                    str(event.new_assignee_id)
                    if event.new_assignee_id
                    else None
                ),
                "new_assignee_email": (
                    event.new_assignee.user.email
                    if event.new_assignee
                    else None
                ),
                "changed_by": event.changed_by.email,
                "reason": event.reason,
                "created_at": event.created_at.isoformat(),
            }
            for event in history
        ])