
from uuid import UUID

from apps.leads.models import Lead
from apps.opportunities.models import Opportunity

from .registry import ReadOnlyTool, registry


def get_lead(*, context, arguments):
    """
    Retrieve one lead from the authorized organization.

    Read-only: no records are modified.
    """

    if set(arguments) != {"lead_id"}:
        return {
            "error": "invalid_arguments",
            "message": "Provide only lead_id.",
        }

    raw_id = arguments["lead_id"]

    if not isinstance(raw_id, str):
        return {"error": "invalid_lead_id"}

    try:
        lead_id = UUID(raw_id)
    except (ValueError, AttributeError):
        return {"error": "invalid_lead_id"}

    lead = (
        Lead.objects
        .filter(
            pk=lead_id,
            organization_id=context.organization.id,
        )
        .first()
    )

    if lead is None:
        return {
            "error": "lead_not_found",
            "message": "Lead not found.",
        }

    # Query related opportunities within the same tenant.
    opportunity = (
        Opportunity.objects
        .filter(
            organization_id=context.organization.id,
            source_lead_id=lead.id,
        )
        .only("id", "status")
        .first()
    )

    return {
        "id": str(lead.id),
        "title": lead.title,
        "status": lead.status,
        "is_archived": lead.is_archived,
        "created_at": lead.created_at.isoformat(),

        "assigned_to_id": (
            str(lead.assigned_to_id)
            if lead.assigned_to_id
            else None
        ),

        "company_id": (
            str(lead.company_id)
            if lead.company_id
            else None
        ),

        "contact_id": (
            str(lead.contact_id)
            if lead.contact_id
            else None
        ),

        "converted_to_opportunity": (
            opportunity is not None
        ),

        "opportunity_id": (
            str(opportunity.id)
            if opportunity
            else None
        ),

        "opportunity_status": (
            opportunity.status
            if opportunity
            else None
        ),
    }


def register_lead_tools():
    registry.register(
        ReadOnlyTool(
            name="get_lead",
            description=(
                "Retrieve the status, assignment, "
                "archive state and opportunity conversion "
                "details of one CRM lead by UUID."
            ),
            handler=get_lead,
        )
    )
