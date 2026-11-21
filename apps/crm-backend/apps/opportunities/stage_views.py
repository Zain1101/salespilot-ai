from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.tenancy.permissions import IsTenantMember
from .models import (
    Opportunity,
    OpportunityStageHistory,
)
from .serializers import (
    OpportunitySerializer,
    OpportunityStageTransitionSerializer,
)
from .services import move_opportunity_stage


class OpportunityStageTransitionView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]

    def post(self, request, organization_id, pk):
        serializer = OpportunityStageTransitionSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        try:
            opportunity, moved = move_opportunity_stage(
                organization_id=organization_id,
                opportunity_id=pk,
                changed_by=request.user,
                target_stage_id=serializer.validated_data[
                    "stage_id"
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
            {
                "moved": moved,
                "opportunity": OpportunitySerializer(
                    opportunity
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class OpportunityStageHistoryView(APIView):
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
            OpportunityStageHistory.objects
            .filter(
                organization_id=organization_id,
                opportunity_id=pk,
            )
            .select_related(
                "old_stage",
                "new_stage",
                "changed_by",
            )
            .order_by("-created_at", "-id")
        )

        return Response([
            {
                "id": str(event.id),
                "old_stage": str(event.old_stage_id),
                "old_stage_name": event.old_stage.name,
                "new_stage": str(event.new_stage_id),
                "new_stage_name": event.new_stage.name,
                "changed_by": event.changed_by.email,
                "reason": event.reason,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ])