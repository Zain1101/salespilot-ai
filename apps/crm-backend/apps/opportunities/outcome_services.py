from decimal import Decimal

from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction
from django.utils import timezone

from apps.organizations.models import (
    Organization,
    Membership,
)
from apps.pipelines.models import PipelineStage
from common.tenancy.services import require_organization_role

from .models import Opportunity, OpportunityOutcomeHistory


CLOSING_ROLES = [
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.MANAGER,
]


@transaction.atomic
def close_opportunity(
    *,
    organization_id,
    opportunity_id,
    changed_by,
    outcome,
    actual_value=None,
    loss_reason="",
):
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
        raise PermissionDenied(
            "Organization is unavailable."
        )

    require_organization_role(
        user=changed_by,
        organization_id=organization.id,
        allowed_roles=CLOSING_ROLES,
    )

    opportunity = (
        Opportunity.objects
        .select_for_update(of=("self",))
        .filter(
            pk=opportunity_id,
            organization=organization,
        )
        .first()
    )

    if opportunity is None:
        raise ValidationError("Opportunity not found.")

    if outcome not in (
        Opportunity.Status.WON,
        Opportunity.Status.LOST,
    ):
        raise ValidationError(
            "Outcome must be 'won' or 'lost'."
        )

    # Repeating exactly the same outcome is safe.
    if opportunity.status == outcome:
        return opportunity, False

    # A previously closed opportunity cannot be
    # switched to another outcome.
    if opportunity.status != Opportunity.Status.OPEN:
        raise ValidationError(
            "This opportunity is already closed."
        )

    if not opportunity.pipeline_id or not opportunity.stage_id:
        raise ValidationError(
            "Opportunity must have a valid pipeline and stage."
        )

    pipeline = opportunity.pipeline

    if (
        pipeline.organization_id != organization.id
        or not pipeline.is_active
    ):
        raise ValidationError(
            "Opportunity pipeline is invalid or inactive."
        )

    current_stage = PipelineStage.objects.filter(
        pk=opportunity.stage_id,
        pipeline_id=pipeline.id,
    ).first()

    if current_stage is None:
        raise ValidationError(
            "Opportunity stage does not belong to its pipeline."
        )

    if outcome == Opportunity.Status.WON:
        final_stage = (
            PipelineStage.objects
            .filter(pipeline_id=pipeline.id)
            .order_by("-position", "-id")
            .first()
        )

        if final_stage is None or current_stage.id != final_stage.id:
            raise ValidationError(
                "Move the opportunity to the final "
                "pipeline stage before marking it Won."
            )

        if actual_value is None:
            raise ValidationError(
                "Actual deal value is required for Won deals."
            )

        if actual_value < Decimal("0"):
            raise ValidationError(
                "Actual deal value cannot be negative."
            )

        opportunity.actual_value = actual_value
        opportunity.loss_reason = ""

    else:
        if not loss_reason.strip():
            raise ValidationError(
                "Loss reason is required for Lost deals."
            )

        opportunity.actual_value = None
        opportunity.loss_reason = loss_reason.strip()

    previous_status = opportunity.status

    opportunity.status = outcome
    opportunity.closed_at = timezone.now()
    opportunity.closed_by = changed_by

    opportunity.save(
        update_fields=[
            "status",
            "actual_value",
            "closed_at",
            "closed_by",
            "loss_reason",
            "updated_at",
        ]
    )

    OpportunityOutcomeHistory.objects.create(
        organization=organization,
        opportunity=opportunity,
        old_status=previous_status,
        new_status=outcome,
        actual_value=opportunity.actual_value,
        loss_reason=opportunity.loss_reason,
        changed_by=changed_by,
    )

    return opportunity, True