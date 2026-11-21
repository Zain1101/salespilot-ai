import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Opportunity(models.Model):

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    pipeline = models.ForeignKey(
        "pipelines.Pipeline",
        on_delete=models.PROTECT,
        related_name="opportunities",
        null=True,
        blank=True,
    )

    stage = models.ForeignKey(
        "pipelines.PipelineStage",
        on_delete=models.PROTECT,
        related_name="opportunities",
        null=True,
        blank=True,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="opportunities",
    )

    source_lead = models.OneToOneField(
        "leads.Lead",
        on_delete=models.PROTECT,
        related_name="converted_opportunity",
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="opportunities",
    )

    contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="opportunities",
    )

    title = models.CharField(max_length=255)

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

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )

    converted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="converted_opportunities",
    )

    converted_at = models.DateTimeField(
        auto_now_add=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at", "-id"]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="opp_org_status_idx",
            ),
        ]

    def __str__(self):
        return self.title