
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from apps.organizations.models import (
    Organization,
    Membership,
)
from apps.opportunities.models import Opportunity
from apps.opportunities.timeline_services import (
    get_opportunity_timeline,
)


MAX_TIMELINE_EVENTS = 15
MAX_EVENT_DESCRIPTION = 1200


def build_opportunity_context(
    *,
    organization_id,
    opportunity_id,
    requested_by,
):
    """
    Retrieve tenant-authorized, read-only CRM data
    and prepare a bounded context for the AI.

    This function performs no CRM modifications
    and makes no external LLM requests.
    """

    if not requested_by.is_authenticated or not requested_by.is_active:
        raise PermissionDenied("Authentication required.")

    organization = Organization.objects.filter(
        pk=organization_id,
        is_active=True,
    ).first()

    if organization is None:
        raise PermissionDenied(
            "Organization is unavailable."
        )

    membership = Membership.objects.filter(
        organization=organization,
        user=requested_by,
        is_active=True,
    ).first()

    if membership is None:
        raise PermissionDenied(
            "You do not have access to this organization."
        )

    opportunity = get_object_or_404(
        Opportunity.objects.select_related(
            "pipeline",
            "stage",
        ),
        pk=opportunity_id,
        organization=organization,
    )

    timeline = get_opportunity_timeline(
        opportunity=opportunity,
        limit=MAX_TIMELINE_EVENTS,
    )

    recent_events = []

    for event in timeline["events"]:
        recent_events.append({
            "event_type": event["event_type"],
            "timestamp": event["timestamp"],
            "title": event["title"][:255],
            "description": (
                event.get("description") or ""
            )[:MAX_EVENT_DESCRIPTION],
        })

    context = {
        "organization_id": str(organization.id),

        "opportunity": {
            "id": str(opportunity.id),
            "title": opportunity.title,
            "status": opportunity.status,
            "currency": opportunity.currency,

            "estimated_value": str(
                opportunity.estimated_value
            ),

            "actual_value": (
                str(opportunity.actual_value)
                if opportunity.actual_value is not None
                else None
            ),

            "pipeline": (
                opportunity.pipeline.name
                if opportunity.pipeline_id
                else None
            ),

            "stage": (
                opportunity.stage.name
                if opportunity.stage_id
                else None
            ),

            "stage_probability": (
                opportunity.stage.probability
                if opportunity.stage_id
                else None
            ),
        },

        "recent_events": recent_events,
        "timeline_has_more": timeline["has_more"],
        "context_read_only": True,
    }

    return context
