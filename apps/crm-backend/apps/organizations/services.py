import uuid

from django.db import transaction
from django.utils.text import slugify

from .models import Membership, Organization, OrganizationInvitation
from datetime import timedelta

from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .models import (
    Organization,
    Membership,
    OrganizationInvitation,
    MembershipRoleAudit,
)
from .models import MembershipStatusAudit

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

@transaction.atomic
def update_member_role(
    *,
    organization,
    changed_by,
    membership_id,
    new_role,
):
    # Lock the organization to serialize membership
    # management operations that follow this convention.
    locked_org = Organization.objects.select_for_update().get(
        pk=organization.pk
    )

    if not locked_org.is_active:
        raise PermissionDenied("Organization is inactive.")

    if not changed_by.is_authenticated or not changed_by.is_active:
        raise PermissionDenied("Unauthorized user.")

    actor_membership = (
        Membership.objects.select_for_update()
        .filter(
            organization=locked_org,
            user=changed_by,
            is_active=True,
        )
        .first()
    )

    if actor_membership is None:
        raise PermissionDenied(
            "You are not an active organization member."
        )

    if actor_membership.role not in [
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
    ]:
        raise PermissionDenied(
            "You cannot manage employee roles."
        )

    target = (
        Membership.objects.select_for_update()
        .select_related("user")
        .filter(
            pk=membership_id,
            organization=locked_org,
        )
        .first()
    )

    if target is None:
        raise ValidationError("Membership not found.")

    if not target.is_active or not target.user.is_active:
        raise ValidationError(
            "Cannot change the role of an inactive member."
        )

    if target.user_id == changed_by.pk:
        raise PermissionDenied(
            "You cannot change your own role."
        )

    allowed_roles = [
        Membership.Role.ADMIN,
        Membership.Role.MANAGER,
        Membership.Role.SALES_REP,
        Membership.Role.VIEWER,
    ]

    if new_role not in allowed_roles:
        raise ValidationError("Invalid target role.")

    if target.role == Membership.Role.OWNER:
        raise PermissionDenied(
            "Owner roles cannot be changed here."
        )

    # Admins cannot modify or create other admins.
    if actor_membership.role == Membership.Role.ADMIN:
        if target.role == Membership.Role.ADMIN:
            raise PermissionDenied(
                "Admins cannot modify other admins."
            )

        if new_role == Membership.Role.ADMIN:
            raise PermissionDenied(
                "Only an Owner can assign Admin roles."
            )

    if target.role == new_role:
        return target

    previous_role = target.role

    target.role = new_role
    target.save(update_fields=["role"])

    MembershipRoleAudit.objects.create(
        organization=locked_org,
        membership=target,
        changed_by=changed_by,
        old_role=previous_role,
        new_role=new_role,
    )

    return target

@transaction.atomic
def change_membership_status(
    *,
    organization,
    changed_by,
    membership_id,
    active,
):
    if not isinstance(active, bool):
        raise ValidationError("Active must be a boolean.")

    # Serialize organization membership changes.
    locked_org = (
        Organization.objects
        .select_for_update()
        .get(pk=organization.pk)
    )

    if not locked_org.is_active:
        raise PermissionDenied("Organization is inactive.")

    if (
        not changed_by
        or not changed_by.is_authenticated
        or not changed_by.is_active
    ):
        raise PermissionDenied("Unauthorized user.")

    actor = (
        Membership.objects
        .select_for_update()
        .filter(
            organization=locked_org,
            user=changed_by,
            is_active=True,
        )
        .first()
    )

    if actor is None or actor.role not in [
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
    ]:
        raise PermissionDenied(
            "You cannot manage membership status."
        )

    target = (
        Membership.objects
        .select_for_update()
        .select_related("user")
        .filter(
            pk=membership_id,
            organization=locked_org,
        )
        .first()
    )

    if target is None:
        raise ValidationError("Membership not found.")

    if target.user_id == changed_by.pk:
        raise PermissionDenied(
            "You cannot change your own membership status."
        )

    if target.role == Membership.Role.OWNER:
        raise PermissionDenied(
            "Owner memberships cannot be modified here."
        )

    if actor.role == Membership.Role.ADMIN:
        if target.role == Membership.Role.ADMIN:
            raise PermissionDenied(
                "Admins cannot manage other admins."
            )

    if active and not target.user.is_active:
        raise ValidationError(
            "Cannot reactivate a globally inactive user."
        )

    if target.is_active == active:
        return target

    old_status = target.is_active

    target.is_active = active
    target.save(update_fields=["is_active"])

    MembershipStatusAudit.objects.create(
        organization=locked_org,
        membership=target,
        changed_by=changed_by,
        old_status=old_status,
        new_status=active,
    )

    return target