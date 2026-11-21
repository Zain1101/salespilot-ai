from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction

from apps.companies.models import Company
from apps.organizations.models import Organization, Membership

from common.tenancy.services import require_organization_role

from .models import Contact, CRMArchiveAudit


EDIT_ROLES = [
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.MANAGER,
    Membership.Role.SALES_REP,
]


@transaction.atomic
def change_archive_status(
    *,
    organization_id,
    changed_by,
    entity_type,
    entity_id,
    archived,
):
    if not isinstance(archived, bool):
        raise ValidationError("Archived must be a boolean.")

    # Use a shared organization lock to serialize
    # membership-sensitive CRM operations.
    organization = (
        Organization.objects
        .select_for_update()
        .filter(pk=organization_id, is_active=True)
        .first()
    )

    if organization is None:
        raise PermissionDenied("Organization unavailable.")

    require_organization_role(
        user=changed_by,
        organization_id=organization.id,
        allowed_roles=EDIT_ROLES,
    )

    if entity_type == CRMArchiveAudit.EntityType.COMPANY:
        model = Company

    elif entity_type == CRMArchiveAudit.EntityType.CONTACT:
        model = Contact

    else:
        raise ValidationError("Invalid entity type.")

    record = (
        model.objects
        .select_for_update()
        .filter(
            pk=entity_id,
            organization=organization,
        )
        .first()
    )

    if record is None:
        raise ValidationError("CRM record not found.")

    # A contact shouldn't be restored under
    # an archived company.
    if (
        entity_type == CRMArchiveAudit.EntityType.CONTACT
        and not archived
        and record.company_id is not None
    ):
        company = Company.objects.get(pk=record.company_id)

        if company.is_archived:
            raise ValidationError(
                "Restore the associated company first."
            )

    # No database update or new audit event
    # if the status is already correct.
    if record.is_archived == archived:
        return record

    previous_status = record.is_archived

    record.is_archived = archived
    record.save(update_fields=["is_archived", "updated_at"])

    CRMArchiveAudit.objects.create(
        organization=organization,
        entity_type=entity_type,
        entity_id=record.id,
        changed_by=changed_by,
        old_status=previous_status,
        new_status=archived,
    )

    return record