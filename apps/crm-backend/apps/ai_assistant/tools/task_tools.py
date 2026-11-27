
from datetime import timezone as dt_timezone

from django.utils import timezone

from apps.tasks.models import SalesTask

from .registry import ReadOnlyTool, registry


MAX_TASK_RESULTS = 20


def list_my_tasks(*, context, arguments):
    """
    Return pending tasks assigned to the
    authenticated user's active membership.

    No database modifications.
    """

    allowed_arguments = {"overdue_only", "limit"}

    if not set(arguments).issubset(allowed_arguments):
        return {
            "error": "invalid_arguments",
            "message": "Only overdue_only and limit are allowed.",
        }

    overdue_only = arguments.get("overdue_only", False)
    limit = arguments.get("limit", 10)

    if not isinstance(overdue_only, bool):
        return {"error": "invalid_overdue_filter"}

    if type(limit) is not int or not 1 <= limit <= MAX_TASK_RESULTS:
        return {"error": "invalid_limit"}

    now = timezone.now()

    tasks = SalesTask.objects.filter(
        organization_id=context.organization.id,
        assigned_to_id=context.membership.id,
        status=SalesTask.Status.PENDING,
    )

    if overdue_only:
        tasks = tasks.filter(due_at__lt=now)

    # Stable ordering, earliest deadlines first.
    tasks = tasks.order_by("due_at", "id")[:limit]

    results = []

    for task in tasks:
        results.append({
            "id": str(task.id),
            "title": task.title[:255],
            "priority": task.priority,
            "status": task.status,
            "due_at": (
                task.due_at.isoformat()
                if task.due_at
                else None
            ),
            "is_overdue": (
                task.due_at is not None
                and task.due_at < now
            ),
            "related_record": {
                "lead_id": (
                    str(task.lead_id)
                    if task.lead_id
                    else None
                ),
                "opportunity_id": (
                    str(task.opportunity_id)
                    if task.opportunity_id
                    else None
                ),
                "company_id": (
                    str(task.company_id)
                    if task.company_id
                    else None
                ),
                "contact_id": (
                    str(task.contact_id)
                    if task.contact_id
                    else None
                ),
            },
        })

    return {
        "tasks": results,
        "returned_count": len(results),
        "limit": limit,
        "overdue_only": overdue_only,
        "read_only": True,
    }


def register_task_tools():
    registry.register(
        ReadOnlyTool(
            name="list_my_tasks",
            description=(
                "List pending CRM tasks assigned to the "
                "authenticated salesperson. Optionally "
                "show only overdue tasks. Returns a "
                "maximum of 20 tasks."
            ),
            handler=list_my_tasks,
        )
    )
