from django.db.models import Q

from apps.activities.models import Activity
from apps.tasks.models import (
    SalesTask,
    SalesTaskStatusHistory,
)
from apps.leads.models import LeadStatusHistory

from .models import (
    Opportunity,
    OpportunityStageHistory,
    OpportunityOutcomeHistory,
)


def get_opportunity_timeline(*, opportunity, limit=20):
    """
    Build a read-only timeline from existing
    tenant-scoped CRM records.

    Returns the most recent 'limit' events.
    """

    organization_id = opportunity.organization_id
    lead_id = opportunity.source_lead_id

    # Retrieve one extra event from each source
    # to determine whether more events exist.
    fetch_limit = limit + 1

    events = []

    def add_event(
        *,
        event_id,
        event_type,
        timestamp,
        actor,
        title,
        description="",
        metadata=None,
    ):
        events.append({
            "id": str(event_id),
            "event_type": event_type,
            "timestamp": timestamp.isoformat(),
            "actor": actor,
            "title": title,
            "description": description,
            "metadata": metadata or {},
            "_sort_at": timestamp,
        })

    # 1. Calls, emails, meetings and notes.
    activities = (
        Activity.objects
        .filter(organization_id=organization_id)
        .filter(
            Q(opportunity_id=opportunity.id)
            | Q(lead_id=lead_id)
        )
        .select_related("created_by")
        .order_by("-occurred_at", "-created_at", "-id")[
            :fetch_limit
        ]
    )

    for activity in activities:
        add_event(
            event_id=activity.id,
            event_type="activity",
            timestamp=activity.occurred_at,
            actor=activity.created_by.email,
            title=activity.subject,
            description=activity.description,
            metadata={
                "activity_type": activity.activity_type,
                "linked_entity": (
                    "opportunity"
                    if activity.opportunity_id
                    else "lead"
                ),
            },
        )

    task_filter = (
        Q(opportunity_id=opportunity.id)
        | Q(lead_id=lead_id)
    )

    # 2. Tasks created for this opportunity/lead.
    tasks = (
        SalesTask.objects
        .filter(organization_id=organization_id)
        .filter(task_filter)
        .select_related("created_by", "assigned_to__user")
        .order_by("-created_at", "-id")[:fetch_limit]
    )

    for task in tasks:
        add_event(
            event_id=task.id,
            event_type="task_created",
            timestamp=task.created_at,
            actor=task.created_by.email,
            title=f"Task created: {task.title}",
            description=task.description,
            metadata={
                "task_id": str(task.id),
                "assigned_to": task.assigned_to.user.email,
                "due_at": task.due_at.isoformat(),
                "priority": task.priority,
            },
        )

    # 3. Task completion/cancellation events.
    task_events = (
        SalesTaskStatusHistory.objects
        .filter(organization_id=organization_id)
        .filter(
            Q(task__opportunity_id=opportunity.id)
            | Q(task__lead_id=lead_id)
        )
        .select_related("task", "changed_by")
        .order_by("-created_at", "-id")[:fetch_limit]
    )

    for event in task_events:
        add_event(
            event_id=event.id,
            event_type="task_status",
            timestamp=event.created_at,
            actor=event.changed_by.email,
            title=(
                f"Task {event.new_status}: "
                f"{event.task.title}"
            ),
            description=event.reason,
            metadata={
                "task_id": str(event.task_id),
                "old_status": event.old_status,
                "new_status": event.new_status,
            },
        )

    # 4. Opportunity pipeline movements.
    stage_events = (
        OpportunityStageHistory.objects
        .filter(
            organization_id=organization_id,
            opportunity_id=opportunity.id,
        )
        .select_related(
            "old_stage",
            "new_stage",
            "changed_by",
        )
        .order_by("-created_at", "-id")[:fetch_limit]
    )

    for event in stage_events:
        add_event(
            event_id=event.id,
            event_type="stage_changed",
            timestamp=event.created_at,
            actor=event.changed_by.email,
            title=(
                f"Stage changed: "
                f"{event.old_stage.name} → "
                f"{event.new_stage.name}"
            ),
            description=event.reason,
            metadata={
                "old_stage_id": str(event.old_stage_id),
                "new_stage_id": str(event.new_stage_id),
            },
        )

    # 5. Won/Lost deal outcomes.
    outcome_events = (
        OpportunityOutcomeHistory.objects
        .filter(
            organization_id=organization_id,
            opportunity_id=opportunity.id,
        )
        .select_related("changed_by")
        .order_by("-created_at", "-id")[:fetch_limit]
    )

    for event in outcome_events:
        add_event(
            event_id=event.id,
            event_type="deal_outcome",
            timestamp=event.created_at,
            actor=event.changed_by.email,
            title=f"Opportunity marked {event.new_status}",
            description=event.loss_reason,
            metadata={
                "old_status": event.old_status,
                "new_status": event.new_status,
                "actual_value": (
                    str(event.actual_value)
                    if event.actual_value is not None
                    else None
                ),
                "currency": opportunity.currency,
            },
        )

    # 6. Qualification history from the source Lead.
    lead_events = (
        LeadStatusHistory.objects
        .filter(
            organization_id=organization_id,
            lead_id=lead_id,
        )
        .select_related("changed_by")
        .order_by("-created_at", "-id")[:fetch_limit]
    )

    for event in lead_events:
        add_event(
            event_id=event.id,
            event_type="lead_status",
            timestamp=event.created_at,
            actor=event.changed_by.email,
            title=(
                f"Lead status: "
                f"{event.old_status} → "
                f"{event.new_status}"
            ),
            description=event.reason,
            metadata={
                "lead_id": str(lead_id),
                "old_status": event.old_status,
                "new_status": event.new_status,
            },
        )

    # Sort all event types together by timestamp.
    events.sort(
        key=lambda item: (
            item["_sort_at"],
            item["id"],
        ),
        reverse=True,
    )

    has_more = len(events) > limit

    result = events[:limit]

    # Internal sort keys should not appear in API JSON.
    for event in result:
        del event["_sort_at"]

    return {
        "opportunity_id": str(opportunity.id),
        "source_lead_id": str(lead_id),
        "limit": limit,
        "has_more": has_more,
        "events": result,
    }