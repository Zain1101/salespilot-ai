from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations.models import Membership
from common.tenancy.permissions import IsTenantMember

from .models import Notification
from .serializers import NotificationSerializer


class NotificationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def get_recipient_membership(request, organization_id):
    return get_object_or_404(
        Membership,
        organization_id=organization_id,
        user=request.user,
        is_active=True,
        organization__is_active=True,
    )


class NotificationListView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]

    def get(self, request, organization_id):

        membership = get_recipient_membership(
            request,
            organization_id,
        )

        notifications = Notification.objects.filter(
            organization_id=organization_id,
            recipient=membership,
        )

        unread = request.query_params.get("unread")

        if unread not in (None, "true", "false"):
            return Response(
                {"detail": "unread must be true or false."},
                status=400,
            )

        if unread == "true":
            notifications = notifications.filter(
                is_read=False,
                resolved_at__isnull=True,
            )

        elif unread == "false":
            notifications = notifications.filter(
                is_read=True,
            )

        # A fixed sorting order makes the inbox
        # deterministic and suitable for pagination.
        notifications = notifications.order_by(
            "-created_at",
            "-id",
        )

        paginator = NotificationPagination()
        page = paginator.paginate_queryset(
            notifications,
            request,
            view=self,
        )

        return paginator.get_paginated_response(
            NotificationSerializer(page, many=True).data
        )


class NotificationUnreadCountView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]

    def get(self, request, organization_id):

        membership = get_recipient_membership(
            request,
            organization_id,
        )

        count = Notification.objects.filter(
            organization_id=organization_id,
            recipient=membership,
            is_read=False,
            resolved_at__isnull=True,
        ).count()

        return Response({
            "unread_count": count,
        })


class NotificationMarkReadView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]

    @transaction.atomic
    def post(self, request, organization_id, pk):

        membership = get_recipient_membership(
            request,
            organization_id,
        )

        notification = get_object_or_404(
            Notification.objects.select_for_update(
                of=("self",)
            ),
            pk=pk,
            organization_id=organization_id,
            recipient=membership,
        )

        changed = not notification.is_read

        if changed:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(
                update_fields=[
                    "is_read",
                    "read_at",
                ]
            )

        return Response({
            "changed": changed,
            "notification": NotificationSerializer(
                notification
            ).data,
        })