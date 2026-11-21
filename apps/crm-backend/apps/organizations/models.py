import uuid

from django.conf import settings
from django.db import models
import hashlib
import secrets

from datetime import timedelta
from django.utils import timezone

class Organization(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(max_length=255)

    slug = models.SlugField(
        max_length=255,
        unique=True,
    )

    timezone = models.CharField(
        max_length=100,
        default="UTC",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_organizations",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Membership(models.Model):

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Sales Manager"
        SALES_REP = "sales_rep", "Sales Representative"
        VIEWER = "viewer", "Viewer"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )

    is_active = models.BooleanField(default=True)

    joined_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="unique_organization_membership",
            )
        ]

    def __str__(self):
        return (
            f"{self.user.email} - "
            f"{self.organization.name} ({self.role})"
        )
        
class OrganizationInvitation(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="invitations",
    )

    email = models.EmailField()

    role = models.CharField(
        max_length=20,
        choices=Membership.Role.choices,
    )

    token_hash = models.CharField(
        max_length=64,
        unique=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_invitations",
    )

    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(token):
        return hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

    @property
    def is_valid(self):
        return (
            self.status == self.Status.PENDING
            and timezone.now() < self.expires_at
        )

    def __str__(self):
        return (
            f"{self.email} invited to "
            f"{self.organization.name}"
        )
        
class MembershipRoleAudit(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="role_audits",
    )

    membership = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        related_name="role_audits",
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="performed_role_changes",
    )

    old_role = models.CharField(max_length=20)
    new_role = models.CharField(max_length=20)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.old_role} -> {self.new_role} "
            f"for {self.membership.user.email}"
        )
        
class MembershipStatusAudit(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="membership_status_audits",
    )

    membership = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        related_name="status_audits",
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="membership_status_changes",
    )

    old_status = models.BooleanField()
    new_status = models.BooleanField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"Membership {self.membership_id}: "
            f"{self.old_status} -> {self.new_status}"
        )