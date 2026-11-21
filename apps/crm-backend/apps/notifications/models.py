from django.db import models

# Create your models here.
import uuid

from django.db import models
from django.db.models import Q


class Notification(models.Model):

    class Type(models.TextChoices):
        TASK_DUE_SOON = "task_due_soon", "Task Due Soon"
        TASK_OVERDUE = "task_overdue", "Task Overdue"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="notifications",
    )

    recipient = models.ForeignKey(
        "organizations.Membership",
        on_delete=models.PROTECT,
        related_name="notifications",
    )

    task = models.ForeignKey(
        "tasks.SalesTask",
        on_delete=models.PROTECT,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=30,
        choices=Type.choices,
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    is_read = models.BooleanField(default=False)

    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at", "-id"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "task",
                    "notification_type",
                ],
                name="unique_task_notification_type",
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_read=False, read_at__isnull=True)
                    | Q(is_read=True, read_at__isnull=False)
                ),
                name="notification_read_state_consistent",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "organization",
                    "recipient",
                    "is_read",
                    "created_at",
                ],
                name="notif_inbox_lookup_idx",
            ),
        ]

    def __str__(self):
        return f"{self.notification_type}: {self.title}"