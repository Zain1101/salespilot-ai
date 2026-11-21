from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.organizations.models import Organization, Membership
from apps.leads.models import Lead
from apps.companies.models import Company
from apps.contacts.models import Contact
from apps.opportunities.models import Opportunity
from common.tenancy.services import require_organization_role

from .models import SalesTask, SalesTaskStatusHistory


MANAGEMENT_ROLES = [
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.MANAGER,
]

TASK_CREATOR_ROLES = MANAGEMENT_ROLES + [
    Membership.Role.SALES_REP,
]

ENTITY_MODELS = {
    "lead": Lead,
    "company": Company,
    "contact": Contact,
    "opportunity": Opportunity,
}


@transaction.atomic
def create_sales_task(
    *,
    organization_id,
    created_by,
    title,
    assigned_to_id,
    due_at,
    description="",
    priority=SalesTask.Priority.MEDIUM,
    lead_id=None,
    company_id=None,
    contact_id=None,
    opportunity_id=None,
):
    organization = (
        Organization.objects
        .select_for_update()
        .filter(pk=organization_id, is_active=True)
        .first()
    )

    if organization is None:
        raise PermissionDenied("Organization is unavailable.")

    membership = require_organization_role(
        user=created_by,
        organization_id=organization.id,
        allowed_roles=TASK_CREATOR_ROLES,
    )

    assignee = (
        Membership.objects
        .select_for_update()
        .filter(
            pk=assigned_to_id,
            organization=organization,
            is_active=True,
            user__is_active=True,
            role__in=TASK_CREATOR_ROLES,
        )
        .first()
    )

    if assignee is None:
        raise ValidationError(
            "Assignee must be an eligible active member."
        )

    # Never trust a client to assign a salesperson
    # a task belonging to another employee.
    if membership.role == Membership.Role.SALES_REP:
        if assignee.pk != membership.pk:
            raise PermissionDenied(
                "Sales representatives can only create tasks for themselves."
            )

    linked = {
        "lead": lead_id,
        "company": company_id,
        "contact": contact_id,
        "opportunity": opportunity_id,
    }

    supplied = {
        key: value
        for key, value in linked.items()
        if value is not None
    }

    if len(supplied) != 1:
        raise ValidationError(
            "Exactly one linked CRM entity is required."
        )

    entity_type, entity_id = next(iter(supplied.items()))

    entity = ENTITY_MODELS[entity_type].objects.filter(
        pk=entity_id,
        organization=organization,
    ).first()

    if entity is None:
        raise ValidationError(
            "Linked CRM entity was not found in this organization."
        )

    if getattr(entity, "is_archived", False):
        raise ValidationError(
            "Cannot create a task for an archived entity."
        )

    if not title.strip():
        raise ValidationError("Task title is required.")

    if due_at <= timezone.now():
        raise ValidationError("Task due date must be in the future.")

    return SalesTask.objects.create(
        organization=organization,
        created_by=created_by,
        assigned_to=assignee,
        title=title.strip(),
        description=description,
        priority=priority,
        due_at=due_at,
        **{f"{entity_type}_id": entity_id},
    )


@transaction.atomic
def change_task_status(
    *,
    organization_id,
    task_id,
    changed_by,
    new_status,
    reason="",
):
    organization = (
        Organization.objects
        .select_for_update()
        .filter(pk=organization_id, is_active=True)
        .first()
    )

    if organization is None:
        raise PermissionDenied("Organization is unavailable.")

    membership = require_organization_role(
        user=changed_by,
        organization_id=organization.id,
        allowed_roles=TASK_CREATOR_ROLES,
    )

    task = (
        SalesTask.objects
        .select_for_update(of=("self",))
        .filter(pk=task_id, organization=organization)
        .first()
    )

    if task is None:
        raise ValidationError("Task not found.")

    if new_status not in (
        SalesTask.Status.COMPLETED,
        SalesTask.Status.CANCELLED,
    ):
        raise ValidationError("Invalid task status transition.")

    is_manager = membership.role in MANAGEMENT_ROLES

    if not is_manager:
        if new_status != SalesTask.Status.COMPLETED:
            raise PermissionDenied(
                "Sales representatives cannot cancel tasks."
            )

        if task.assigned_to_id != membership.pk:
            raise PermissionDenied(
                "You can only complete your assigned tasks."
            )

    if task.status == new_status:
        return task, False

    if task.status != SalesTask.Status.PENDING:
        raise ValidationError(
            "Only pending tasks can change status."
        )

    old_status = task.status
    task.status = new_status

    if new_status == SalesTask.Status.COMPLETED:
        task.completed_at = timezone.now()
        task.completed_by = changed_by

    task.save(
        update_fields=[
            "status",
            "completed_at",
            "completed_by",
            "updated_at",
        ]
    )

    SalesTaskStatusHistory.objects.create(
        organization=organization,
        task=task,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        reason=reason,
    )

    return task, True