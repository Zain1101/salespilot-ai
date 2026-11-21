from django.shortcuts import get_object_or_404

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.tenancy.permissions import IsTenantMember

from .models import Opportunity
from .timeline_serializers import (
    OpportunityTimelineQuerySerializer,
)
from .timeline_services import get_opportunity_timeline


class OpportunityTimelineView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]

    def get(self, request, organization_id, pk):
        serializer = OpportunityTimelineQuerySerializer(
            data=request.query_params
        )

        serializer.is_valid(raise_exception=True)

        opportunity = get_object_or_404(
            Opportunity,
            pk=pk,
            organization_id=organization_id,
        )

        timeline = get_opportunity_timeline(
            opportunity=opportunity,
            limit=serializer.validated_data["limit"],
        )

        return Response(timeline)