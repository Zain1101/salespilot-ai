from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase

from apps.organizations.models import Membership
from apps.organizations.services import create_organization
from apps.companies.models import Company
from apps.contacts.models import Contact

from .models import Lead


User = get_user_model()


class LeadAPITests(APITestCase):

    def setUp(self):
        self.owner_a = User.objects.create_user(
            email="lead-owner-a@example.com",
            password="SecureTest@2026!",
        )

        self.owner_b = User.objects.create_user(
            email="lead-owner-b@example.com",
            password="SecureTest@2026!",
        )

        self.viewer = User.objects.create_user(
            email="lead-viewer@example.com",
            password="SecureTest@2026!",
        )

        self.sales_rep = User.objects.create_user(
            email="lead-rep@example.com",
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

        self.rep_membership = Membership.objects.create(
            organization=self.org_a,
            user=self.sales_rep,
            role=Membership.Role.SALES_REP,
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

        self.contact_b = Contact.objects.create(
            organization=self.org_b,
            company=self.company_b,
            created_by=self.owner_b,
            first_name="Private",
        )

        self.lead_a = Lead.objects.create(
            organization=self.org_a,
            title="Automation Inquiry",
            company=self.company_a,
            contact=self.contact_a,
            created_by=self.owner_a,
        )

        self.lead_b = Lead.objects.create(
            organization=self.org_b,
            title="Private Lead",
            created_by=self.owner_b,
        )

        self.list_url = reverse(
            "lead-list-create",
            kwargs={"organization_id": self.org_a.id},
        )

    def test_owner_can_create_lead(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.post(
            self.list_url,
            {
                "title": "New AI Inquiry",
                "company": str(self.company_a.id),
                "contact": str(self.contact_a.id),
                "source": "website",
                "priority": "high",
            },
        )

        self.assertEqual(response.status_code, 201)

        lead = Lead.objects.get(id=response.data["id"])

        self.assertEqual(lead.organization, self.org_a)
        self.assertEqual(lead.status, Lead.Status.NEW)

    def test_listing_is_tenant_scoped(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)

        ids = {
            item["id"] for item in response.data["results"]
        }

        self.assertIn(str(self.lead_a.id), ids)
        self.assertNotIn(str(self.lead_b.id), ids)

    def test_foreign_company_is_rejected(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.post(
            self.list_url,
            {
                "title": "Invalid Lead",
                "company": str(self.company_b.id),
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_foreign_contact_is_rejected(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.post(
            self.list_url,
            {
                "title": "Invalid Contact Lead",
                "contact": str(self.contact_b.id),
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_mismatched_company_contact_is_rejected(self):
        second_company = Company.objects.create(
            organization=self.org_a,
            created_by=self.owner_a,
            name="Second Company",
        )

        self.client.force_authenticate(user=self.owner_a)

        response = self.client.post(
            self.list_url,
            {
                "title": "Mismatched Lead",
                "company": str(second_company.id),
                "contact": str(self.contact_a.id),
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_foreign_assignee_is_rejected(self):
        other_membership = Membership.objects.get(
            organization=self.org_b,
            user=self.owner_b,
        )

        self.client.force_authenticate(user=self.owner_a)

        response = self.client.patch(
            reverse(
                "lead-detail",
                kwargs={
                    "organization_id": self.org_a.id,
                    "pk": self.lead_a.id,
                },
            ),
            {
                "assigned_to": str(other_membership.id),
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_sales_rep_can_be_assigned(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.post(
            reverse(
                "lead-assign",
                kwargs={
                    "organization_id": self.org_a.id,
                    "pk": self.lead_a.id,
                },
            ),
            {"assigned_to": str(self.rep_membership.id)},
        )

        self.assertEqual(response.status_code, 200)

        self.lead_a.refresh_from_db()
        self.assertEqual(
            self.lead_a.assigned_to,
            self.rep_membership,
        )

    def test_viewer_cannot_create_lead(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(
            self.list_url,
            {"title": "Unauthorized Lead"},
        )

        self.assertEqual(response.status_code, 403)

    def test_cross_tenant_lead_detail_is_hidden(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.get(
            reverse(
                "lead-detail",
                kwargs={
                    "organization_id": self.org_a.id,
                    "pk": self.lead_b.id,
                },
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_inactive_member_is_denied(self):
        self.rep_membership.is_active = False
        self.rep_membership.save(
            update_fields=["is_active"]
        )

        self.client.force_authenticate(user=self.sales_rep)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 403)

    def test_status_cannot_be_changed_directly(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.patch(
            reverse(
                "lead-detail",
                kwargs={
                    "organization_id": self.org_a.id,
                    "pk": self.lead_a.id,
                },
            ),
            {"status": "qualified"},
        )

        self.assertEqual(response.status_code, 200)

        self.lead_a.refresh_from_db()
        self.assertEqual(
            self.lead_a.status,
            Lead.Status.NEW,
        )

    def test_negative_value_is_rejected(self):
        self.client.force_authenticate(user=self.owner_a)

        response = self.client.post(
            self.list_url,
            {
                "title": "Invalid Value",
                "estimated_value": "-500",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_anonymous_access_is_rejected(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 401)