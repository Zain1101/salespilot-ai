import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Lead(models.Model):

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        QUALIFIED = "qualified", "Qualified"
        DISQUALIFIED = "disqualified", "Disqualified"

    class Source(models.TextChoices):
        WEBSITE = "website", "Website"
        REFERRAL = "referral", "Referral"
        OUTBOUND = "outbound", "Outbound"
        SOCIAL_MEDIA = "social_media", "Social Media"
        EMAIL = "email", "Email Campaign"
        OTHER = "other", "Other"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="leads",
    )

    title = models.CharField(max_length=255)

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="leads",
    )

    contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="leads",
    )

    assigned_to = models.ForeignKey(
        "organizations.Membership",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_leads",
    )

    source = models.CharField(
        max_length=30,
        choices=Source.choices,
        default=Source.OTHER,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.NEW,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    estimated_value = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    currency = models.CharField(
        max_length=3,
        choices=[
            ("PKR", "PKR"),
            ("USD", "USD"),
            ("EUR", "EUR"),
        ],
        default="PKR",
    )

    description = models.TextField(blank=True)

    is_archived = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_leads",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="lead_org_status_idx",
            ),
            models.Index(
                fields=["organization", "assigned_to"],
                name="lead_org_assignee_idx",
            ),
            models.Index(
                fields=["organization", "created_at"],
                name="lead_org_created_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(estimated_value__gte=0),
                name="lead_estimated_value_nonnegative",
            ),
        ]

    def __str__(self):
        return self.title