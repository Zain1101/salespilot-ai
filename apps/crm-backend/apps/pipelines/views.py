from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.tenancy.permissions import IsTenantMember
from common.tenancy.services import get_active_membership

from .models import Pipeline
from .serializers import (
    PipelineSerializer,
    PipelineCreateSerializer,
)
from .services import create_sales_pipeline


class PipelineListCreateView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]

    def get(self, request, organization_id):
        pipelines = (
            Pipeline.objects
            .filter(organization_id=organization_id)
            .prefetch_related("stages")
            .order_by("-is_default", "name")
        )

        return Response(
            PipelineSerializer(pipelines, many=True).data
        )

    def post(self, request, organization_id):
        serializer = PipelineCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        try:
            pipeline = create_sales_pipeline(
                organization_id=organization_id,
                created_by=request.user,
                name=serializer.validated_data["name"],
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

        pipeline = Pipeline.objects.prefetch_related(
            "stages"
        ).get(pk=pipeline.pk)

        return Response(
            PipelineSerializer(pipeline).data,
            status=status.HTTP_201_CREATED,
        )


class PipelineDetailView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]

    def get(self, request, organization_id, pk):
        pipeline = get_object_or_404(
            Pipeline.objects.prefetch_related("stages"),
            pk=pk,
            organization_id=organization_id,
        )

        return Response(
            PipelineSerializer(pipeline).data
        )