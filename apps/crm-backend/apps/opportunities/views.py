from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from common.tenancy.mixins import TenantQuerysetMixin
from common.tenancy.permissions import IsTenantMember

from .models import Opportunity
from .serializers import OpportunitySerializer
from .services import convert_lead_to_opportunity


class OpportunityPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class OpportunityListView(
    TenantQuerysetMixin,
    generics.ListAPIView,
):
    queryset = Opportunity.objects.select_related(
        "company",
        "contact",
        "converted_by",
    )

    serializer_class = OpportunitySerializer
    pagination_class = OpportunityPagination

    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]


class OpportunityDetailView(
    TenantQuerysetMixin,
    generics.RetrieveAPIView,
):
    queryset = Opportunity.objects.select_related(
        "company",
        "contact",
        "converted_by",
    )

    serializer_class = OpportunitySerializer

    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]


class LeadConversionView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]

    def post(self, request, organization_id, pk):
        try:
            opportunity, created = convert_lead_to_opportunity(
                organization_id=organization_id,
                lead_id=pk,
                converted_by=request.user,
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
            OpportunitySerializer(opportunity).data,
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )