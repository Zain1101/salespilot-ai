from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.tenancy.permissions import IsTenantMember

from .models import Activity
from .serializers import (
    ActivityCreateSerializer,
    ActivitySerializer,
)
from .services import create_activity


class ActivityPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ActivityListCreateView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]

    def get(self, request, organization_id):

        queryset = (
            Activity.objects
            .filter(organization_id=organization_id)
            .select_related("created_by")
            .order_by("-occurred_at", "-created_at", "-id")
        )

        activity_type = request.query_params.get("type")

        if activity_type:
            if activity_type not in Activity.Type.values:
                return Response(
                    {"detail": "Invalid activity type."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            queryset = queryset.filter(
                activity_type=activity_type
            )

        entity_filters = {
            "lead_id": "lead_id",
            "company_id": "company_id",
            "contact_id": "contact_id",
            "opportunity_id": "opportunity_id",
        }

        supplied_filters = [
            field for field in entity_filters
            if field in request.query_params
        ]

        if len(supplied_filters) > 1:
            return Response(
                {
                    "detail": (
                        "Filter by only one CRM entity at a time."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if supplied_filters:
            from uuid import UUID

            field = supplied_filters[0]
            raw_value = request.query_params[field]

            try:
                entity_id = UUID(raw_value)
            except (ValueError, AttributeError):
                return Response(
                    {"detail": f"Invalid {field}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            queryset = queryset.filter(
                **{entity_filters[field]: entity_id}
            )

        paginator = ActivityPagination()
        page = paginator.paginate_queryset(
            queryset,
            request,
            view=self,
        )

        serializer = ActivitySerializer(
            page,
            many=True,
        )

        return paginator.get_paginated_response(
            serializer.data
        )

    def post(self, request, organization_id):

        serializer = ActivityCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        try:
            activity = create_activity(
                organization_id=organization_id,
                created_by=request.user,
                **serializer.validated_data,
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
            ActivitySerializer(activity).data,
            status=status.HTTP_201_CREATED,
        )


class ActivityDetailView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]

    def get(self, request, organization_id, pk):

        activity = get_object_or_404(
            Activity.objects.select_related("created_by"),
            pk=pk,
            organization_id=organization_id,
        )

        return Response(
            ActivitySerializer(activity).data
        )