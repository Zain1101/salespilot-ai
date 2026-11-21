import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class SalesTask(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="sales_tasks",
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    assigned_to = models.ForeignKey(
        "organizations.Membership",
        on_delete=models.PROTECT,
        related_name="assigned_sales_tasks",
    )

    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
    )

    due_at = models.DateTimeField()

    lead = models.ForeignKey(
        "leads.Lead",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sales_tasks",
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sales_tasks",
    )

    contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sales_tasks",
    )

    opportunity = models.ForeignKey(
        "opportunities.Opportunity",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sales_tasks",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_sales_tasks",
    )

    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="completed_sales_tasks",
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_at", "id"]

        indexes = [
            models.Index(
                fields=["organization", "status", "due_at"],
                name="task_org_status_due_idx",
            ),
            models.Index(
                fields=["assigned_to", "status"],
                name="task_assignee_status_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        lead__isnull=False,
                        company__isnull=True,
                        contact__isnull=True,
                        opportunity__isnull=True,
                    )
                    | Q(
                        lead__isnull=True,
                        company__isnull=False,
                        contact__isnull=True,
                        opportunity__isnull=True,
                    )
                    | Q(
                        lead__isnull=True,
                        company__isnull=True,
                        contact__isnull=False,
                        opportunity__isnull=True,
                    )
                    | Q(
                        lead__isnull=True,
                        company__isnull=True,
                        contact__isnull=True,
                        opportunity__isnull=False,
                    )
                ),
                name="task_exactly_one_entity",
            ),

            models.CheckConstraint(
                condition=(
                    Q(
                        status="completed",
                        completed_at__isnull=False,
                        completed_by__isnull=False,
                    )
                    |
                    (
                        ~Q(status="completed")
                        & Q(completed_at__isnull=True)
                        & Q(completed_by__isnull=True)
                    )
                ),
                name="task_completion_consistent",
            ),
        ]

    def __str__(self):
        return self.title


class SalesTaskStatusHistory(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="task_status_events",
    )

    task = models.ForeignKey(
        SalesTask,
        on_delete=models.PROTECT,
        related_name="status_history",
    )

    old_status = models.CharField(
        max_length=12,
        choices=SalesTask.Status.choices,
    )

    new_status = models.CharField(
        max_length=12,
        choices=SalesTask.Status.choices,
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="task_status_changes",
    )

    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.task_id}: {self.old_status} -> {self.new_status}"