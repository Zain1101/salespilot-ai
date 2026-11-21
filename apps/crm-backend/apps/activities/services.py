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
from apps.leads.models import Lead
from apps.companies.models import Company
from apps.contacts.models import Contact
from apps.opportunities.models import Opportunity

from common.tenancy.services import require_organization_role

from .models import Activity


ACTIVITY_ROLES = [
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.MANAGER,
    Membership.Role.SALES_REP,
]

ENTITY_MODELS = {
    "lead": Lead,
    "company": Company,
    "contact": Contact,
    "opportunity": Opportunity,
}


@transaction.atomic
def create_activity(
    *,
    organization_id,
    created_by,
    activity_type,
    subject,
    description="",
    occurred_at=None,
    lead_id=None,
    company_id=None,
    contact_id=None,
    opportunity_id=None,
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
        user=created_by,
        organization_id=organization.id,
        allowed_roles=ACTIVITY_ROLES,
    )

    target_ids = {
        "lead": lead_id,
        "company": company_id,
        "contact": contact_id,
        "opportunity": opportunity_id,
    }

    supplied = {
        entity_type: entity_id
        for entity_type, entity_id in target_ids.items()
        if entity_id is not None
    }

    if len(supplied) != 1:
        raise ValidationError(
            "Provide exactly one linked CRM entity."
        )

    entity_type, entity_id = next(iter(supplied.items()))

    entity_model = ENTITY_MODELS[entity_type]

    entity = entity_model.objects.filter(
        pk=entity_id,
        organization=organization,
    ).first()

    if entity is None:
        raise ValidationError(
            "Linked CRM entity was not found "
            "in this organization."
        )

    # Archived entities cannot receive new activities.
    if getattr(entity, "is_archived", False):
        raise ValidationError(
            "Cannot log a new activity against "
            "an archived entity."
        )

    if activity_type not in Activity.Type.values:
        raise ValidationError(
            "Invalid activity type."
        )

    subject = subject.strip()

    if not subject:
        raise ValidationError(
            "Activity subject is required."
        )

    if occurred_at is None:
        occurred_at = timezone.now()

    if occurred_at > timezone.now():
        raise ValidationError(
            "An activity cannot occur in the future. "
            "Use a scheduled task for future interactions."
        )

    return Activity.objects.create(
        organization=organization,
        activity_type=activity_type,
        subject=subject,
        description=description,
        occurred_at=occurred_at,
        created_by=created_by,
        **{f"{entity_type}_id": entity_id},
    )