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