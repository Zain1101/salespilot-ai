
from uuid import UUID

from apps.opportunities.models import Opportunity

from .registry import ReadOnlyTool, registry


def get_opportunity(*, context, arguments):
    """
    Retrieve a single Opportunity.

    Organization identity comes exclusively from
    the trusted execution context.

    This function performs no database writes.
    """

    # Validate the exact arguments we accept.
    if set(arguments) != {"opportunity_id"}:
        return {
            "error": "invalid_arguments",
            "message": "Provide only opportunity_id.",
        }

    raw_id = arguments["opportunity_id"]

    if not isinstance(raw_id, str):
        return {
            "error": "invalid_opportunity_id",
        }

    try:
        opportunity_id = UUID(raw_id)
    except (ValueError, AttributeError):
        return {
            "error": "invalid_opportunity_id",
        }

    # Important:
    # Both the Opportunity ID and organization
    # are included in the database query.
    opportunity = (
        Opportunity.objects
        .select_related("pipeline", "stage")
        .filter(
            pk=opportunity_id,
            organization_id=context.organization.id,
        )
        .first()
    )

    if opportunity is None:
        return {
            "error": "opportunity_not_found",
            "message": "Opportunity not found.",
        }

    return {
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
        "closed_at": (
            opportunity.closed_at.isoformat()
            if opportunity.closed_at
            else None
        ),
        "loss_reason": opportunity.loss_reason,
        "source_lead_id": (
            str(opportunity.source_lead_id)
            if opportunity.source_lead_id
            else None
        ),
    }


def register_opportunity_tools():
    registry.register(
        ReadOnlyTool(
            name="get_opportunity",
            description=(
                "Retrieve the status, pipeline stage, "
                "financial value and basic details of "
                "a specific CRM opportunity by UUID."
            ),
            handler=get_opportunity,
        )
    )
