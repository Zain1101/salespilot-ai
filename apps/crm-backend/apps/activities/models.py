import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Activity(models.Model):

    class Type(models.TextChoices):
        CALL = "call", "Call"
        EMAIL = "email", "Email"
        MEETING = "meeting", "Meeting"
        NOTE = "note", "Note"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="crm_activities",
    )

    activity_type = models.CharField(
        max_length=20,
        choices=Type.choices,
    )

    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # The person who recorded the activity.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="crm_activities",
    )

    # When the interaction actually occurred.
    occurred_at = models.DateTimeField(
        default=timezone.now,
    )

    # When it was recorded in SalesPilot.
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    lead = models.ForeignKey(
        "leads.Lead",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="activities",
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="activities",
    )

    contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="activities",
    )

    opportunity = models.ForeignKey(
        "opportunities.Opportunity",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="activities",
    )

    class Meta:
        ordering = ["-occurred_at", "-created_at", "-id"]

        indexes = [
            models.Index(
                fields=["organization", "occurred_at"],
                name="activity_org_date_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        lead__isnull=False,
                        company__isnull=True,
                        contact__isnull=True,
                        opportunity__isnull=True,
                    )
                    |
                    Q(
                        lead__isnull=True,
                        company__isnull=False,
                        contact__isnull=True,
                        opportunity__isnull=True,
                    )
                    |
                    Q(
                        lead__isnull=True,
                        company__isnull=True,
                        contact__isnull=False,
                        opportunity__isnull=True,
                    )
                    |
                    Q(
                        lead__isnull=True,
                        company__isnull=True,
                        contact__isnull=True,
                        opportunity__isnull=False,
                    )
                ),
                name="activity_exactly_one_entity",
            ),
        ]

    def __str__(self):
        return f"{self.activity_type}: {self.subject}"