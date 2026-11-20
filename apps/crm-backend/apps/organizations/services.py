import uuid

from django.db import transaction
from django.utils.text import slugify

from .models import Membership, Organization


@transaction.atomic
def create_organization(*, name, owner, timezone="UTC"):

    if not owner or not owner.is_active or not owner.pk:
        raise ValueError("A valid active owner is required")

    name = name.strip()

    if not name:
        raise ValueError("Organization name is required")

    base_slug = slugify(name)[:180] or "organization"
    unique_suffix = uuid.uuid4().hex[:12]

    organization = Organization.objects.create(
        name=name,
        slug=f"{base_slug}-{unique_suffix}",
        timezone=timezone,
        created_by=owner,
    )

    Membership.objects.create(
        organization=organization,
        user=owner,
        role=Membership.Role.OWNER,
    )

    return organization