import uuid

from django.conf import settings
from django.db import models


class Contact(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="contacts",
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        related_name="contacts",
        null=True,
        blank=True,
    )

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(
        max_length=100,
        blank=True,
    )

    email = models.EmailField(blank=True)

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    job_title = models.CharField(
        max_length=150,
        blank=True,
    )

    department = models.CharField(
        max_length=150,
        blank=True,
    )

    linkedin_url = models.URLField(blank=True)

    city = models.CharField(
        max_length=100,
        blank=True,
    )

    country = models.CharField(
        max_length=100,
        blank=True,
    )

    notes = models.TextField(blank=True)

    is_primary = models.BooleanField(default=False)

    is_archived = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_contacts",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["first_name", "last_name", "id"]

        indexes = [
            models.Index(
                fields=["organization", "email"],
                name="contact_org_email_idx",
            ),
            models.Index(
                fields=["organization", "company"],
                name="contact_org_company_idx",
            ),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()