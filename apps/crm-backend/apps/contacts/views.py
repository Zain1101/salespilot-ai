from uuid import UUID

from django.db.models import Q

from rest_framework import generics, serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from common.tenancy.mixins import TenantQuerysetMixin
from common.tenancy.permissions import IsTenantEditor

from .models import Contact
from .serializers import ContactSerializer


class ContactPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ContactListCreateView(
    TenantQuerysetMixin,
    generics.ListCreateAPIView,
):
    queryset = Contact.objects.select_related(
        "company", "created_by"
    )

    serializer_class = ContactSerializer
    pagination_class = ContactPagination

    permission_classes = [
        IsAuthenticated,
        IsTenantEditor,
    ]

    def get_queryset(self):
        queryset = super().get_queryset()

        archived = self.request.query_params.get(
            "archived", "false"
        ).lower()

        if archived == "true":
            queryset = queryset.filter(is_archived=True)
        else:
            queryset = queryset.filter(is_archived=False)

        search = self.request.query_params.get(
            "search", ""
        ).strip()

        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(job_title__icontains=search)
                | Q(company__name__icontains=search)
            )

        company_id = self.request.query_params.get(
            "company_id"
        )

        if company_id:
            try:
                company_uuid = UUID(company_id)
            except (ValueError, AttributeError):
                raise serializers.ValidationError({
                    "company_id": "Invalid company UUID."
                })

            queryset = queryset.filter(
                company_id=company_uuid
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(
            organization_id=self.kwargs["organization_id"],
            created_by=self.request.user,
        )


class ContactDetailView(
    TenantQuerysetMixin,
    generics.RetrieveUpdateAPIView,
):
    queryset = Contact.objects.select_related(
        "company", "created_by"
    )

    serializer_class = ContactSerializer

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