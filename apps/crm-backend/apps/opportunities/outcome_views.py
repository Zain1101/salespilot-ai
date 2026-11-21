from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.tenancy.permissions import IsTenantMember

from .models import Opportunity, OpportunityOutcomeHistory
from .serializers import (
    OpportunitySerializer,
    OpportunityCloseSerializer,
)
from .outcome_services import close_opportunity


class OpportunityCloseView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]

    def post(self, request, organization_id, pk):
        serializer = OpportunityCloseSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        try:
            opportunity, closed = close_opportunity(
                organization_id=organization_id,
                opportunity_id=pk,
                changed_by=request.user,
                outcome=serializer.validated_data["outcome"],
                actual_value=serializer.validated_data.get(
                    "actual_value"
                ),
                loss_reason=serializer.validated_data.get(
                    "loss_reason", ""
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
            {
                "closed": closed,
                "opportunity": OpportunitySerializer(
                    opportunity
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class OpportunityOutcomeHistoryView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]

    def get(self, request, organization_id, pk):
        if not Opportunity.objects.filter(
            pk=pk,
            organization_id=organization_id,
        ).exists():
            return Response(
                {"detail": "Opportunity not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        events = (
            OpportunityOutcomeHistory.objects
            .filter(
                organization_id=organization_id,
                opportunity_id=pk,
            )
            .select_related("changed_by")
            .order_by("-created_at", "-id")
        )

        return Response([
            {
                "id": str(event.id),
                "old_status": event.old_status,
                "new_status": event.new_status,
                "actual_value": (
                    str(event.actual_value)
                    if event.actual_value is not None
                    else None
                ),
                "loss_reason": event.loss_reason,
                "changed_by": event.changed_by.email,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ])