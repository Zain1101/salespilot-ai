from django.db.models import Q

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from common.tenancy.mixins import TenantQuerysetMixin
from common.tenancy.permissions import IsTenantEditor

from .models import Company
from .serializers import CompanySerializer


class CompanyPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class CompanyListCreateView(
    TenantQuerysetMixin,
    generics.ListCreateAPIView,
):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    pagination_class = CompanyPagination

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
                Q(name__icontains=search)
                | Q(industry__icontains=search)
                | Q(domain__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(
            organization_id=self.kwargs["organization_id"],
            created_by=self.request.user,
        )


class CompanyDetailView(
    TenantQuerysetMixin,
    generics.RetrieveUpdateAPIView,
):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

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