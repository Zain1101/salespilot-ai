from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction

from apps.organizations.models import (
    Organization,
    Membership,
)
from common.tenancy.services import require_organization_role

from .models import Lead, LeadStatusHistory


ALLOWED_TRANSITIONS = {
    Lead.Status.NEW: {
        Lead.Status.CONTACTED,
        Lead.Status.DISQUALIFIED,
    },
    Lead.Status.CONTACTED: {
        Lead.Status.QUALIFIED,
        Lead.Status.DISQUALIFIED,
    },
    Lead.Status.QUALIFIED: {
        Lead.Status.CONTACTED,
    },
    Lead.Status.DISQUALIFIED: {
        Lead.Status.NEW,
    },
}

EDIT_ROLES = [
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.MANAGER,
    Membership.Role.SALES_REP,
]


@transaction.atomic
def transition_lead_status(
    *,
    organization_id,
    lead_id,
    changed_by,
    new_status,
    reason="",
):
    # Lock organization first, consistently with
    # our other membership-sensitive services.
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
        raise PermissionDenied("Organization unavailable.")

    require_organization_role(
        user=changed_by,
        organization_id=organization.id,
        allowed_roles=EDIT_ROLES,
    )

    lead = (
        Lead.objects
        .select_for_update()
        .filter(
            pk=lead_id,
            organization=organization,
        )
        .first()
    )

    if lead is None:
        raise ValidationError("Lead not found.")

    if lead.is_archived:
        raise ValidationError(
            "Archived leads cannot change status."
        )

    if new_status not in Lead.Status.values:
        raise ValidationError("Invalid lead status.")

    # A repeated request does not create
    # duplicate audit history.
    if lead.status == new_status:
        return lead

    allowed = ALLOWED_TRANSITIONS.get(lead.status, set())

    if new_status not in allowed:
        raise ValidationError(
            f"Cannot transition from "
            f"'{lead.status}' to '{new_status}'."
        )

    previous_status = lead.status

    lead.status = new_status
    lead.save(update_fields=["status", "updated_at"])

    LeadStatusHistory.objects.create(
        lead=lead,
        organization=organization,
        changed_by=changed_by,
        old_status=previous_status,
        new_status=new_status,
        reason=reason,
    )

    return lead