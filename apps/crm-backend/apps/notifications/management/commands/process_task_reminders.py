
from django.core.management.base import BaseCommand
from django.db import connection

from apps.notifications.services import process_task_reminders


REMINDER_LOCK_ID = 73110504


class Command(BaseCommand):
    help = "Process pending task reminders safely."

    def handle(self, *args, **options):

        if connection.vendor != "postgresql":
            raise RuntimeError(
                "This reminder scheduler requires PostgreSQL."
            )

        lock_acquired = False

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_try_advisory_lock(%s)",
                    [REMINDER_LOCK_ID],
                )
                lock_acquired = cursor.fetchone()[0]

            if not lock_acquired:
                self.stdout.write(
                    "Reminder processor already running. "
                    "Skipping this execution."
                )
                return

            result = process_task_reminders()

            self.stdout.write(
                self.style.SUCCESS(
                    "Reminder processing finished. "
                    f"Due soon: {result['due_soon_created']}, "
                    f"Overdue: {result['overdue_created']}, "
                    f"Total created: {result['total_created']}"
                )
            )

        finally:
            if lock_acquired:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT pg_advisory_unlock(%s)",
                        [REMINDER_LOCK_ID],
                    )
