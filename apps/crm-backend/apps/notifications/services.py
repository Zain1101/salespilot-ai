from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.organizations.models import Organization
from apps.tasks.models import SalesTask

from .models import Notification


REMINDER_WINDOW = timedelta(hours=24)


def process_task_reminders(*, now=None):
    """
    Generate in-app reminders for pending tasks.

    This function is safe to execute repeatedly.
    The database unique constraint prevents
    duplicate notifications.
    """

    now = now or timezone.now()
    upcoming_cutoff = now + REMINDER_WINDOW

    created_due_soon = 0
    created_overdue = 0

    organization_ids = list(
        Organization.objects.filter(
            is_active=True,
        ).values_list("id", flat=True)
    )

    # Process one organization per transaction.
    # Use the same organization-first locking
    # convention as our existing Task services.
    for organization_id in organization_ids:

        with transaction.atomic():

            organization = (
                Organization.objects
                .select_for_update()
                .filter(
                    pk=organization_id,
                    is_active=True,
                )
                .first()
            )

            if organization is None:
                continue

            tasks = (
                SalesTask.objects
                .select_for_update(of=("self",))
                .select_related("assigned_to")
                .filter(
                    organization=organization,
                    status=SalesTask.Status.PENDING,
                    due_at__lte=upcoming_cutoff,
                    assigned_to__is_active=True,
                    assigned_to__user__is_active=True,
                    assigned_to__organization=organization,
                )
                .order_by("due_at", "id")
            )

            for task in tasks:

                if task.due_at <= now:
                    notification_type = (
                        Notification.Type.TASK_OVERDUE
                    )
                    title = "Task overdue"
                    message = (
                        f"Task '{task.title}' is overdue. "
                        "Please review the pending follow-up."
                    )
                else:
                    notification_type = (
                        Notification.Type.TASK_DUE_SOON
                    )
                    title = "Task due soon"
                    message = (
                        f"Task '{task.title}' is due within "
                        "the next 24 hours."
                    )

                _, created = Notification.objects.get_or_create(
                    task=task,
                    notification_type=notification_type,
                    defaults={
                        "organization": organization,
                        "recipient": task.assigned_to,
                        "title": title,
                        "message": message,
                    },
                )

                if created:
                    if notification_type == (
                        Notification.Type.TASK_OVERDUE
                    ):
                        created_overdue += 1
                    else:
                        created_due_soon += 1

    return {
        "due_soon_created": created_due_soon,
        "overdue_created": created_overdue,
        "total_created": (
            created_due_soon + created_overdue
        ),
    }