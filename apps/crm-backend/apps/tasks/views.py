from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.tenancy.permissions import IsTenantMember

from .models import SalesTask, SalesTaskStatusHistory
from .serializers import (
    SalesTaskCreateSerializer,
    SalesTaskSerializer,
    TaskStatusSerializer,
)
from .services import create_sales_task, change_task_status


class TaskPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class SalesTaskListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsTenantMember]

    def get(self, request, organization_id):
        tasks = (
            SalesTask.objects
            .filter(organization_id=organization_id)
            .select_related("assigned_to__user", "created_by")
        )

        task_status = request.query_params.get("status")

        if task_status:
            if task_status not in SalesTask.Status.values:
                return Response(
                    {"detail": "Invalid task status."},
                    status=400,
                )
            tasks = tasks.filter(status=task_status)

        if request.query_params.get("mine") == "true":
            tasks = tasks.filter(
                assigned_to__user=request.user,
                assigned_to__organization_id=organization_id,
            )

        if request.query_params.get("overdue") == "true":
            tasks = tasks.filter(
                status=SalesTask.Status.PENDING,
                due_at__lt=timezone.now(),
            )

        paginator = TaskPagination()
        page = paginator.paginate_queryset(
            tasks.order_by("due_at", "id"),
            request,
            view=self,
        )

        return paginator.get_paginated_response(
            SalesTaskSerializer(page, many=True).data
        )

    def post(self, request, organization_id):
        serializer = SalesTaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            task = create_sales_task(
                organization_id=organization_id,
                created_by=request.user,
                **serializer.validated_data,
            )
        except PermissionDenied as exc:
            return Response({"detail": str(exc)}, status=403)
        except ValidationError as exc:
            return Response({"detail": exc.messages}, status=400)

        return Response(
            SalesTaskSerializer(task).data,
            status=status.HTTP_201_CREATED,
        )


class SalesTaskDetailView(APIView):
    permission_classes = [IsAuthenticated, IsTenantMember]

    def get(self, request, organization_id, pk):
        task = get_object_or_404(
            SalesTask.objects.select_related(
                "assigned_to__user", "created_by"
            ),
            pk=pk,
            organization_id=organization_id,
        )

        return Response(SalesTaskSerializer(task).data)


class SalesTaskStatusView(APIView):
    permission_classes = [IsAuthenticated, IsTenantMember]

    def post(self, request, organization_id, pk):
        serializer = TaskStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            task, changed = change_task_status(
                organization_id=organization_id,
                task_id=pk,
                changed_by=request.user,
                new_status=serializer.validated_data["status"],
                reason=serializer.validated_data.get("reason", ""),
            )
        except PermissionDenied as exc:
            return Response({"detail": str(exc)}, status=403)
        except ValidationError as exc:
            return Response({"detail": exc.messages}, status=400)

        return Response({
            "changed": changed,
            "task": SalesTaskSerializer(task).data,
        })


class SalesTaskHistoryView(APIView):
    permission_classes = [IsAuthenticated, IsTenantMember]

    def get(self, request, organization_id, pk):
        get_object_or_404(
            SalesTask,
            pk=pk,
            organization_id=organization_id,
        )

        events = (
            SalesTaskStatusHistory.objects
            .filter(
                organization_id=organization_id,
                task_id=pk,
            )
            .select_related("changed_by")
            .order_by("-created_at", "-id")
        )

        return Response([
            {
                "id": str(event.id),
                "old_status": event.old_status,
                "new_status": event.new_status,
                "changed_by": event.changed_by.email,
                "reason": event.reason,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ])