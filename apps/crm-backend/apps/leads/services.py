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
from .models import LeadAssignmentHistory

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

@transaction.atomic
def assign_lead(
    *,
    organization_id,
    lead_id,
    changed_by,
    assignee_id=None,
    reason="",
):
    """
    Assign, reassign, or unassign a lead.

    assignee_id=None means unassign the lead.
    """

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
        allowed_roles=[
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
            Membership.Role.MANAGER,
        ],
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
            "Archived leads cannot be assigned."
        )

    new_assignee = None

    if assignee_id is not None:

        new_assignee = (
            Membership.objects
            .select_for_update()
            .filter(
                pk=assignee_id,
                organization=organization,
                is_active=True,
                user__is_active=True,
                role__in=[
                    Membership.Role.OWNER,
                    Membership.Role.ADMIN,
                    Membership.Role.MANAGER,
                    Membership.Role.SALES_REP,
                ],
            )
            .first()
        )

        if new_assignee is None:
            raise ValidationError(
                "Assignee is not an eligible active "
                "member of this organization."
            )

    # Repeating the current assignment is a no-op.
    if lead.assigned_to_id == (
        new_assignee.id if new_assignee else None
    ):
        return lead

    previous_assignee = lead.assigned_to

    lead.assigned_to = new_assignee

    lead.save(
        update_fields=["assigned_to", "updated_at"]
    )

    LeadAssignmentHistory.objects.create(
        organization=organization,
        lead=lead,
        previous_assignee=previous_assignee,
        new_assignee=new_assignee,
        changed_by=changed_by,
        reason=reason,
    )

    return lead