from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction

from apps.leads.models import Lead
from apps.organizations.models import Organization, Membership

from common.tenancy.services import require_organization_role

from .models import Opportunity
from apps.pipelines.models import Pipeline, PipelineStage
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.organizations.models import Organization, Membership
from apps.pipelines.models import PipelineStage

from common.tenancy.services import require_organization_role

from .models import Opportunity, OpportunityStageHistory

CONVERSION_ROLES = [
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.MANAGER,
]


@transaction.atomic
def convert_lead_to_opportunity(
    *,
    organization_id,
    lead_id,
    converted_by,
):
    # Lock the organization first, using the
    # same order as our other CRM services.
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
        user=converted_by,
        organization_id=organization.id,
        allowed_roles=CONVERSION_ROLES,
    )

    lead = (
        Lead.objects
        .select_for_update(of=("self",))
        .select_related("company", "contact")
        .filter(
            pk=lead_id,
            organization=organization,
        )
        .first()
    )

    if lead is None:
        raise ValidationError("Lead not found.")

    # Return the original opportunity if this
    # lead was previously converted.
    existing = Opportunity.objects.filter(
        source_lead=lead,
        organization=organization,
    ).first()

    if existing is not None:
        return existing, False

    if lead.is_archived:
        raise ValidationError(
            "Archived leads cannot be converted."
        )

    if lead.status != Lead.Status.QUALIFIED:
        raise ValidationError(
            "Only qualified leads can be converted."
        )

    if lead.company and lead.company.is_archived:
        raise ValidationError(
            "Restore the associated company first."
        )

    if lead.contact and lead.contact.is_archived:
        raise ValidationError(
            "Restore the associated contact first."
        )
    default_pipeline = (
        Pipeline.objects
        .filter(
            organization=organization,
            is_default=True,
            is_active=True,
        )
        .first()
    )

    if default_pipeline is None:
        raise ValidationError(
            "No active default sales pipeline exists. "
            "Create one before converting leads."
        )

    first_stage = (
        PipelineStage.objects
        .filter(pipeline=default_pipeline)
        .order_by("position", "id")
        .first()
    )

    if first_stage is None:
        raise ValidationError(
            "The default pipeline has no stages."
        )
    opportunity = Opportunity.objects.create(
        organization=organization,
        source_lead=lead,
        company=lead.company,
        contact=lead.contact,
        title=lead.title,
        estimated_value=lead.estimated_value,
        currency=lead.currency,
        converted_by=converted_by,
        status=Opportunity.Status.OPEN,

        # New fields
        pipeline=default_pipeline,
        stage=first_stage,
        )

    return opportunity, True
STAGE_EDIT_ROLES = [
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.MANAGER,
    Membership.Role.SALES_REP,
]


@transaction.atomic
def move_opportunity_stage(
    *,
    organization_id,
    opportunity_id,
    changed_by,
    target_stage_id,
    reason="",
):
    # Lock the organization before taking
    # the opportunity row lock.
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
        allowed_roles=STAGE_EDIT_ROLES,
    )

    # Lock only the opportunity. Do not join
    # nullable pipeline/stage relations here.
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
        raise ValidationError(
            "Opportunity not found."
        )

    if opportunity.status != Opportunity.Status.OPEN:
        raise ValidationError(
            "Only open opportunities can change stages."
        )

    if not opportunity.pipeline_id or not opportunity.stage_id:
        raise ValidationError(
            "Opportunity has no pipeline or current stage."
        )

    current_stage = PipelineStage.objects.filter(
        pk=opportunity.stage_id,
        pipeline_id=opportunity.pipeline_id,
        pipeline__organization=organization,
    ).first()

    if current_stage is None:
        raise ValidationError(
            "Current stage is inconsistent with the pipeline."
        )

    if not current_stage.pipeline.is_active:
        raise ValidationError(
            "The opportunity pipeline is inactive."
        )

    target_stage = PipelineStage.objects.filter(
        pk=target_stage_id,
        pipeline_id=opportunity.pipeline_id,
        pipeline__organization=organization,
        pipeline__is_active=True,
    ).first()

    if target_stage is None:
        raise ValidationError(
            "Target stage does not belong to this opportunity's pipeline."
        )

    if current_stage.pk == target_stage.pk:
        return opportunity, False

    # Compare actual stage order, not numeric
    # positions, which may contain gaps.
    ordered_stage_ids = list(
        PipelineStage.objects.filter(
            pipeline_id=opportunity.pipeline_id,
        )
        .order_by("position", "id")
        .values_list("id", flat=True)
    )

    current_index = ordered_stage_ids.index(
        current_stage.pk
    )

    target_index = ordered_stage_ids.index(
        target_stage.pk
    )

    if abs(target_index - current_index) != 1:
        raise ValidationError(
            "You can only move one stage forward or backward."
        )

    opportunity.stage = target_stage
    opportunity.save(
        update_fields=["stage", "updated_at"]
    )

    OpportunityStageHistory.objects.create(
        organization=organization,
        opportunity=opportunity,
        old_stage=current_stage,
        new_stage=target_stage,
        changed_by=changed_by,
        reason=reason,
    )

    return opportunity, True