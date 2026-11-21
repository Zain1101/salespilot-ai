import uuid

from django.conf import settings
from django.db import models


class Company(models.Model):

    class Size(models.TextChoices):
        MICRO = "1-10", "1–10 employees"
        SMALL = "11-50", "11–50 employees"
        MEDIUM = "51-200", "51–200 employees"
        LARGE = "201-1000", "201–1000 employees"
        ENTERPRISE = "1000+", "More than 1000 employees"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="customer_companies",
    )

    name = models.CharField(max_length=255)

    industry = models.CharField(
        max_length=150,
        blank=True,
    )

    website = models.URLField(blank=True)

    domain = models.CharField(
        max_length=253,
        blank=True,
        db_index=True,
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    email = models.EmailField(blank=True)

    size = models.CharField(
        max_length=20,
        choices=Size.choices,
        blank=True,
    )

    country = models.CharField(
        max_length=100,
        blank=True,
    )

    city = models.CharField(
        max_length=100,
        blank=True,
    )

    address = models.TextField(blank=True)

    description = models.TextField(blank=True)

    is_archived = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_customer_companies",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

        indexes = [
            models.Index(
                fields=["organization", "name"],
                name="company_org_name_idx",
            ),
            models.Index(
                fields=["organization", "is_archived"],
                name="company_org_arch_idx",
            ),
        ]

    def __str__(self):
        return self.name