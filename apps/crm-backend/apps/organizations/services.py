import uuid

from django.db import transaction
from django.utils.text import slugify

from .models import Membership, Organization, OrganizationInvitation
from datetime import timedelta

from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone


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

@transaction.atomic
def create_invitation(*, organization, invited_by, email, role):
    membership = Membership.objects.filter(
        organization=organization,
        user=invited_by,
        is_active=True,
    ).first()

    if (
        not organization.is_active
        or not invited_by.is_active
        or membership is None
        or membership.role not in [
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
        ]
    ):
        raise PermissionDenied(
            "You do not have permission to invite members."
        )

    email = email.strip().lower()

    if not email:
        raise ValidationError("Email is required.")

    if role not in [
        Membership.Role.ADMIN,
        Membership.Role.MANAGER,
        Membership.Role.SALES_REP,
        Membership.Role.VIEWER,
    ]:
        raise ValidationError("Invalid invitation role.")

    from django.contrib.auth import get_user_model

    User = get_user_model()

    existing_user = User.objects.filter(
        email__iexact=email
    ).first()

    if existing_user and Membership.objects.filter(
        organization=organization,
        user=existing_user,
        is_active=True,
    ).exists():
        raise ValidationError(
            "This user is already a member of this organization."
        )

    existing_invitation = OrganizationInvitation.objects.filter(
        organization=organization,
        email__iexact=email,
        status=OrganizationInvitation.Status.PENDING,
        expires_at__gt=timezone.now(),
    ).exists()

    if existing_invitation:
        raise ValidationError(
            "A pending invitation already exists for this email."
        )

    token = OrganizationInvitation.generate_token()

    invitation = OrganizationInvitation.objects.create(
        organization=organization,
        email=email,
        role=role,
        token_hash=OrganizationInvitation.hash_token(token),
        invited_by=invited_by,
        expires_at=timezone.now() + timedelta(days=7),
    )

    return invitation, token

@transaction.atomic
def accept_invitation(*, token, user):
    if not user or not user.is_authenticated or not user.is_active:
        raise PermissionDenied(
            "You must be signed in to accept an invitation."
        )

    token_hash = OrganizationInvitation.hash_token(token)

    invitation = (
        OrganizationInvitation.objects
        .select_for_update()
        .select_related("organization")
        .filter(token_hash=token_hash)
        .first()
    )

    if invitation is None:
        raise ValidationError("Invalid invitation token.")

    if not invitation.is_valid:
        raise ValidationError(
            "Invitation has expired or is no longer valid."
        )

    if not invitation.organization.is_active:
        raise ValidationError(
            "This organization is inactive."
        )

    # Lock and reload the user to get current verification status.
    from django.contrib.auth import get_user_model

    User = get_user_model()

    locked_user = (
        User.objects
        .select_for_update()
        .get(pk=user.pk)
    )

    if not locked_user.is_active:
        raise PermissionDenied("User account is inactive.")

    if not locked_user.email_verified:
        raise PermissionDenied(
            "Please verify your email before accepting invitations."
        )

    if invitation.email.lower() != locked_user.email.lower():
        raise PermissionDenied(
            "This invitation belongs to a different email address."
        )

    user = locked_user

    membership, created = Membership.objects.get_or_create(
        organization=invitation.organization,
        user=user,
        defaults={
            "role": invitation.role,
            "is_active": True,
        },
    )

    if not created:
        if membership.is_active:
            raise ValidationError(
                "You are already a member of this organization."
            )

        membership.role = invitation.role
        membership.is_active = True
        membership.save(update_fields=["role", "is_active"])

    invitation.status = OrganizationInvitation.Status.ACCEPTED
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["status", "accepted_at"])

    return membership