from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase

from apps.organizations.models import Membership
from apps.organizations.services import create_organization
from apps.companies.models import Company

from .models import Contact, CRMArchiveAudit


User = get_user_model()


class ArchiveAPITests(APITestCase):

    def setUp(self):
        self.owner_a = User.objects.create_user(
            email="archive-owner-a@example.com",
            password="SecureTest@2026!",
        )
        self.owner_b = User.objects.create_user(
            email="archive-owner-b@example.com",
            password="SecureTest@2026!",
        )
        self.viewer = User.objects.create_user(
            email="archive-viewer@example.com",
            password="SecureTest@2026!",
        )

        self.org_a = create_organization(
            name="Archive Test A",
            owner=self.owner_a,
        )
        self.org_b = create_organization(
            name="Archive Test B",
            owner=self.owner_b,
        )

        Membership.objects.create(
            organization=self.org_a,
            user=self.viewer,
            role=Membership.Role.VIEWER,
        )

        self.company_a = Company.objects.create(
            organization=self.org_a,
            created_by=self.owner_a,
            name="ABC Logistics",
        )

        self.company_b = Company.objects.create(
            organization=self.org_b,
            created_by=self.owner_b,
            name="Private Business",
        )

        self.contact_a = Contact.objects.create(
            organization=self.org_a,
            company=self.company_a,
            created_by=self.owner_a,
            first_name="Ahmed",
        )

    def url(self, name, org, record):
        return reverse(
            name,
            kwargs={
                "organization_id": org.id,
                "pk": record.id,
            },
        )

    def test_owner_can_archive_company(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.post(
            self.url(
                "company-archive",
                self.org_a,
                self.company_a,
            )
        )

        self.assertEqual(response.status_code, 200)

        self.company_a.refresh_from_db()
        self.assertTrue(self.company_a.is_archived)

        self.assertEqual(
            CRMArchiveAudit.objects.count(),
            1,
        )

    def test_owner_can_restore_company(self):
        self.company_a.is_archived = True
        self.company_a.save(update_fields=["is_archived"])

        self.client.force_authenticate(user=self.owner_a)

        response = self.client.post(
            self.url(
                "company-restore",
                self.org_a,
                self.company_a,
            )
        )

        self.assertEqual(response.status_code, 200)

        self.company_a.refresh_from_db()
        self.assertFalse(self.company_a.is_archived)

    def test_viewer_cannot_archive_company(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(
            self.url(
                "company-archive",
                self.org_a,
                self.company_a,
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_cross_tenant_archive_is_blocked(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.post(
            self.url(
                "company-archive",
                self.org_a,
                self.company_b,
            )
        )

        self.assertEqual(response.status_code, 400)

        self.company_b.refresh_from_db()
        self.assertFalse(self.company_b.is_archived)

    def test_contact_can_be_archived(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.post(
            self.url(
                "contact-archive",
                self.org_a,
                self.contact_a,
            )
        )

        self.assertEqual(response.status_code, 200)

        self.contact_a.refresh_from_db()
        self.assertTrue(self.contact_a.is_archived)

    def test_cannot_restore_contact_under_archived_company(self):
        self.company_a.is_archived = True
        self.company_a.save(update_fields=["is_archived"])

        self.contact_a.is_archived = True
        self.contact_a.save(update_fields=["is_archived"])

        self.client.force_authenticate(user=self.owner_a)

        response = self.client.post(
            self.url(
                "contact-restore",
                self.org_a,
                self.contact_a,
            )
        )

        self.assertEqual(response.status_code, 400)

    def test_repeated_archive_does_not_duplicate_audit(self):
        self.client.force_authenticate(user=self.owner_a)

        url = self.url(
            "company-archive",
            self.org_a,
            self.company_a,
        )

        self.client.post(url)
        self.client.post(url)

        self.assertEqual(
            CRMArchiveAudit.objects.count(),
            1,
        )

    def test_inactive_member_cannot_archive(self):
        Membership.objects.filter(
            organization=self.org_a,
            user=self.viewer,
        ).update(is_active=False)

        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(
            self.url(
                "company-archive",
                self.org_a,
                self.company_a,
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_cannot_archive(self):
        response = self.client.post(
            self.url(
                "company-archive",
                self.org_a,
                self.company_a,
            )
        )

        self.assertEqual(response.status_code, 401)