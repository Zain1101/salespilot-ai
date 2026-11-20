from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Organization
from .serializers import (
    OrganizationSerializer,
    CreateOrganizationSerializer,
)
from .services import create_organization


class OrganizationListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        organizations = Organization.objects.filter(
            memberships__user=request.user,
            memberships__is_active=True,
            is_active=True,
        ).distinct().order_by("name")

        serializer = OrganizationSerializer(
            organizations,
            many=True,
        )

        return Response(serializer.data)

    def post(self, request):
        serializer = CreateOrganizationSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        organization = create_organization(
            name=serializer.validated_data["name"],
            owner=request.user,
            timezone=serializer.validated_data["timezone"],
        )

        return Response(
            OrganizationSerializer(organization).data,
            status=status.HTTP_201_CREATED,
        )


class OrganizationDetailView(generics.RetrieveAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Organization.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
            is_active=True,
        ).distinct()