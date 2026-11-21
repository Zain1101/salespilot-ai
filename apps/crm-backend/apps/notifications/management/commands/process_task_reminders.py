from django.core.management.base import BaseCommand

from apps.notifications.services import (
    process_task_reminders,
)


class Command(BaseCommand):
    help = "Generate due-soon and overdue task notifications."

    def handle(self, *args, **options):

        result = process_task_reminders()

        self.stdout.write(
            self.style.SUCCESS(
                "Reminder processing finished. "
                f"Due soon: {result['due_soon_created']}, "
                f"Overdue: {result['overdue_created']}, "
                f"Total created: {result['total_created']}"
            )
        )