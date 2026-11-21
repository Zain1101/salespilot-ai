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

from .models import Pipeline, PipelineStage


DEFAULT_STAGES = [
    ("Discovery", 10),
    ("Qualification", 25),
    ("Proposal", 50),
    ("Negotiation", 75),
    ("Closing", 90),
]


@transaction.atomic
def create_sales_pipeline(
    *,
    organization_id,
    created_by,
    name,
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
        allowed_roles=[
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
        ],
    )

    name = name.strip()

    if not name:
        raise ValidationError(
            "Pipeline name is required."
        )

    if Pipeline.objects.filter(
        organization=organization,
        name__iexact=name,
    ).exists():
        raise ValidationError(
            "A pipeline with this name already exists."
        )

    # The first pipeline becomes the default.
    has_default = Pipeline.objects.filter(
        organization=organization,
        is_default=True,
    ).exists()

    pipeline = Pipeline.objects.create(
        organization=organization,
        name=name,
        is_default=not has_default,
        created_by=created_by,
    )

    PipelineStage.objects.bulk_create([
        PipelineStage(
            pipeline=pipeline,
            name=stage_name,
            position=index,
            probability=probability,
        )
        for index, (stage_name, probability)
        in enumerate(DEFAULT_STAGES, start=1)
    ])

    return pipeline