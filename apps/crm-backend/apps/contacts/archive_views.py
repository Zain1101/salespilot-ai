from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.tenancy.permissions import IsTenantEditor

from apps.companies.serializers import CompanySerializer

from .models import CRMArchiveAudit
from .serializers import ContactSerializer
from .services import change_archive_status


class ArchiveStatusView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTenantEditor,
    ]

    entity_type = None
    target_archived = None

    def post(self, request, organization_id, pk):

        try:
            record = change_archive_status(
                organization_id=organization_id,
                changed_by=request.user,
                entity_type=self.entity_type,
                entity_id=pk,
                archived=self.target_archived,
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

        if self.entity_type == CRMArchiveAudit.EntityType.COMPANY:
            serializer = CompanySerializer(record)
        else:
            serializer = ContactSerializer(
                record,
                context={
                    "request": request,
                    "view": self,
                },
            )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class CompanyArchiveView(ArchiveStatusView):
    entity_type = CRMArchiveAudit.EntityType.COMPANY
    target_archived = True


class CompanyRestoreView(ArchiveStatusView):
    entity_type = CRMArchiveAudit.EntityType.COMPANY
    target_archived = False


class ContactArchiveView(ArchiveStatusView):
    entity_type = CRMArchiveAudit.EntityType.CONTACT
    target_archived = True


class ContactRestoreView(ArchiveStatusView):
    entity_type = CRMArchiveAudit.EntityType.CONTACT
    target_archived = False