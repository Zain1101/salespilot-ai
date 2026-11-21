from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase

from apps.companies.models import Company
from apps.organizations.models import Membership
from apps.organizations.services import create_organization

from .models import Contact


User = get_user_model()


class ContactAPITests(APITestCase):

    def setUp(self):
        self.owner_a = User.objects.create_user(
            email="owner-a@example.com",
            password="SecureTest@2026!",
        )

        self.owner_b = User.objects.create_user(
            email="owner-b@example.com",
            password="SecureTest@2026!",
        )

        self.viewer = User.objects.create_user(
            email="viewer@example.com",
            password="SecureTest@2026!",
        )

        self.org_a = create_organization(
            name="Agency A",
            owner=self.owner_a,
        )

        self.org_b = create_organization(
            name="Agency B",
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
            name="Private Tech",
        )

        self.contact_a = Contact.objects.create(
            organization=self.org_a,
            company=self.company_a,
            created_by=self.owner_a,
            first_name="Ahmed",
            last_name="Khan",
        )

        self.contact_b = Contact.objects.create(
            organization=self.org_b,
            company=self.company_b,
            created_by=self.owner_b,
            first_name="Private",
        )

        self.list_url = reverse(
            "contact-list-create",
            kwargs={"organization_id": self.org_a.id},
        )

    def test_owner_can_create_contact(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.post(
            self.list_url,
            {
                "first_name": "Sara",
                "last_name": "Ali",
                "company": str(self.company_a.id),
                "email": "sara@example.com",
            },
        )

        self.assertEqual(response.status_code, 201)

        contact = Contact.objects.get(
            id=response.data["id"]
        )

        self.assertEqual(contact.organization, self.org_a)
        self.assertEqual(contact.company, self.company_a)
        self.assertEqual(contact.created_by, self.owner_a)

    def test_cannot_link_foreign_company(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.post(
            self.list_url,
            {
                "first_name": "Unauthorized",
                "company": str(self.company_b.id),
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_cannot_move_contact_to_foreign_company(self):
        self.client.force_authenticate(user=self.owner_a)

        url = reverse(
            "contact-detail",
            kwargs={
                "organization_id": self.org_a.id,
                "pk": self.contact_a.id,
            },
        )

        response = self.client.patch(
            url,
            {"company": str(self.company_b.id)},
        )

        self.assertEqual(response.status_code, 400)

        self.contact_a.refresh_from_db()
        self.assertEqual(self.contact_a.company, self.company_a)

    def test_contact_listing_is_tenant_scoped(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)

        ids = {
            item["id"] for item in response.data["results"]
        }

        self.assertIn(str(self.contact_a.id), ids)
        self.assertNotIn(str(self.contact_b.id), ids)

    def test_foreign_contact_detail_is_hidden(self):
        self.client.force_authenticate(user=self.owner_a)

        url = reverse(
            "contact-detail",
            kwargs={
                "organization_id": self.org_a.id,
                "pk": self.contact_b.id,
            },
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_viewer_can_read_contacts(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_create_contacts(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(
            self.list_url,
            {"first_name": "Blocked"},
        )

        self.assertEqual(response.status_code, 403)

    def test_inactive_member_cannot_access_contacts(self):
        Membership.objects.filter(
            organization=self.org_a,
            user=self.viewer,
        ).update(is_active=False)

        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_access_is_rejected(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 401)

    def test_contact_search(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.get(
            self.list_url,
            {"search": "Ahmed"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_company_filter(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.get(
            self.list_url,
            {"company_id": str(self.company_a.id)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_invalid_company_filter(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.get(
            self.list_url,
            {"company_id": "invalid-uuid"},
        )

        self.assertEqual(response.status_code, 400)

    def test_archived_company_cannot_be_newly_assigned(self):
        self.company_a.is_archived = True
        self.company_a.save(update_fields=["is_archived"])

        self.client.force_authenticate(user=self.owner_a)

        response = self.client.post(
            self.list_url,
            {
                "first_name": "Sara",
                "company": str(self.company_a.id),
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_client_cannot_override_organization(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.post(
            self.list_url,
            {
                "first_name": "Bilal",
                "organization": str(self.org_b.id),
            },
        )

        self.assertEqual(response.status_code, 201)

        contact = Contact.objects.get(id=response.data["id"])
        self.assertEqual(contact.organization, self.org_a)