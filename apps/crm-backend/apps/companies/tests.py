from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase

from apps.organizations.models import Membership
from apps.organizations.services import create_organization

from .models import Company


User = get_user_model()


class CompanyAPITests(APITestCase):

    def setUp(self):
        self.owner_a = User.objects.create_user(
            email="ownera@example.com",
            password="SecureTest@2026!",
        )

        self.owner_b = User.objects.create_user(
            email="ownerb@example.com",
            password="SecureTest@2026!",
        )

        self.viewer = User.objects.create_user(
            email="viewer@example.com",
            password="SecureTest@2026!",
        )

        self.org_a = create_organization(
            name="Company A",
            owner=self.owner_a,
        )

        self.org_b = create_organization(
            name="Company B",
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
            name="Private Company",
        )

        self.list_url = reverse(
            "company-list-create",
            kwargs={"organization_id": self.org_a.id},
        )

    def test_owner_can_create_company(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.post(
            self.list_url,
            {"name": "New Customer"},
        )

        self.assertEqual(response.status_code, 201)

        company = Company.objects.get(
            id=response.data["id"]
        )

        self.assertEqual(company.organization, self.org_a)
        self.assertEqual(company.created_by, self.owner_a)

    def test_list_is_tenant_scoped(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)

        returned_ids = {
            item["id"] for item in response.data["results"]
        }

        self.assertIn(str(self.company_a.id), returned_ids)
        self.assertNotIn(str(self.company_b.id), returned_ids)

    def test_cross_tenant_detail_is_blocked(self):
        self.client.force_authenticate(user=self.owner_a)

        url = reverse(
            "company-detail",
            kwargs={
                "organization_id": self.org_a.id,
                "pk": self.company_b.id,
            },
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_viewer_can_read_companies(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_create_company(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(
            self.list_url,
            {"name": "Unauthorized Company"},
        )

        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_modify_company(self):
        self.client.force_authenticate(user=self.viewer)

        url = reverse(
            "company-detail",
            kwargs={
                "organization_id": self.org_a.id,
                "pk": self.company_a.id,
            },
        )

        response = self.client.patch(
            url,
            {"name": "Changed Name"},
        )

        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 401)

    def test_inactive_member_cannot_access_companies(self):
        Membership.objects.filter(
            organization=self.org_a,
            user=self.viewer,
        ).update(is_active=False)

        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 403)

    def test_client_cannot_override_tenant(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.post(
            self.list_url,
            {
                "name": "Injected Tenant Test",
                "organization": str(self.org_b.id),
            },
        )

        self.assertEqual(response.status_code, 201)

        created = Company.objects.get(
            id=response.data["id"]
        )

        self.assertEqual(created.organization, self.org_a)