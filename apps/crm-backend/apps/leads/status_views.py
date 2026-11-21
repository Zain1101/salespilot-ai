from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.tenancy.permissions import IsTenantEditor
from common.tenancy.services import get_active_membership

from .models import Lead, LeadStatusHistory
from .serializers import (
    LeadSerializer,
    LeadStatusTransitionSerializer,
)
from .services import transition_lead_status


class LeadStatusTransitionView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsTenantEditor,
    ]

    def post(self, request, organization_id, pk):
        serializer = LeadStatusTransitionSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        try:
            lead = transition_lead_status(
                organization_id=organization_id,
                lead_id=pk,
                changed_by=request.user,
                new_status=serializer.validated_data["status"],
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
                context={"request": request, "view": self},
            ).data,
            status=status.HTTP_200_OK,
        )


class LeadStatusHistoryView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsTenantEditor,
    ]

    def get(self, request, organization_id, pk):
        # Verify active membership, independently of
        # the JWT's validity.
        get_active_membership(
            user=request.user,
            organization_id=organization_id,
        )

        # Look up the lead within this tenant only.
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
            LeadStatusHistory.objects
            .filter(
                lead=lead,
                organization_id=organization_id,
            )
            .select_related("changed_by")
            .order_by("-created_at", "-id")
        )

        return Response([
            {
                "id": str(event.id),
                "old_status": event.old_status,
                "new_status": event.new_status,
                "reason": event.reason,
                "changed_by": event.changed_by.email,
                "created_at": event.created_at.isoformat(),
            }
            for event in history
        ])