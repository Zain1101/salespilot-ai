from uuid import UUID

from django.db.models import Q

from rest_framework import generics, serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from common.tenancy.mixins import TenantQuerysetMixin
from common.tenancy.permissions import IsTenantEditor

from .models import Lead
from .serializers import LeadSerializer


class LeadPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class LeadListCreateView(
    TenantQuerysetMixin,
    generics.ListCreateAPIView,
):
    queryset = Lead.objects.select_related(
        "company",
        "contact",
        "assigned_to",
        "assigned_to__user",
    )

    serializer_class = LeadSerializer
    pagination_class = LeadPagination

    permission_classes = [
        IsAuthenticated,
        IsTenantEditor,
    ]

    def get_queryset(self):
        queryset = super().get_queryset()

        search = self.request.query_params.get(
            "search", ""
        ).strip()

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(company__name__icontains=search)
                | Q(contact__first_name__icontains=search)
                | Q(contact__last_name__icontains=search)
            )

        status_value = self.request.query_params.get(
            "status"
        )

        if status_value:
            if status_value not in Lead.Status.values:
                raise serializers.ValidationError({
                    "status": "Invalid lead status."
                })

            queryset = queryset.filter(
                status=status_value
            )

        priority = self.request.query_params.get(
            "priority"
        )

        if priority:
            if priority not in Lead.Priority.values:
                raise serializers.ValidationError({
                    "priority": "Invalid priority."
                })

            queryset = queryset.filter(
                priority=priority
            )

        assigned_to = self.request.query_params.get(
            "assigned_to"
        )

        if assigned_to:
            try:
                membership_id = UUID(assigned_to)
            except (ValueError, AttributeError):
                raise serializers.ValidationError({
                    "assigned_to": "Invalid membership UUID."
                })

            queryset = queryset.filter(
                assigned_to_id=membership_id
            )

        archived = self.request.query_params.get(
            "archived", "false"
        ).lower()

        if archived not in ["true", "false"]:
            raise serializers.ValidationError({
                "archived": "Must be true or false."
            })

        queryset = queryset.filter(
            is_archived=(archived == "true")
        )

        return queryset

    def perform_create(self, serializer):
        serializer.save(
            organization_id=self.kwargs["organization_id"],
            created_by=self.request.user,
        )


class LeadDetailView(
    TenantQuerysetMixin,
    generics.RetrieveUpdateAPIView,
):
    queryset = Lead.objects.select_related(
        "company",
        "contact",
        "assigned_to",
        "assigned_to__user",
    )

    serializer_class = LeadSerializer

    permission_classes = [
        IsAuthenticated,
        IsTenantEditor,
    ]

    http_method_names = [
        "get",
        "patch",
        "head",
        "options",
    ]