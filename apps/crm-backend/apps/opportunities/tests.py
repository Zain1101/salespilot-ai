from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase

from apps.leads.models import Lead
from apps.organizations.models import Membership
from apps.organizations.services import create_organization

from .models import Opportunity


User = get_user_model()


class OpportunityConversionTests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="opportunity-owner@example.com",
            password="SecureTest@2026!",
        )

        self.manager = User.objects.create_user(
            email="opportunity-manager@example.com",
            password="SecureTest@2026!",
        )

        self.sales_rep = User.objects.create_user(
            email="opportunity-rep@example.com",
            password="SecureTest@2026!",
        )

        self.viewer = User.objects.create_user(
            email="opportunity-viewer@example.com",
            password="SecureTest@2026!",
        )

        self.outsider = User.objects.create_user(
            email="opportunity-outsider@example.com",
            password="SecureTest@2026!",
        )

        self.org = create_organization(
            name="Opportunity Test Agency",
            owner=self.owner,
        )

        self.other_org = create_organization(
            name="Other Opportunity Agency",
            owner=self.outsider,
        )

        for user, role in [
            (self.manager, Membership.Role.MANAGER),
            (self.sales_rep, Membership.Role.SALES_REP),
            (self.viewer, Membership.Role.VIEWER),
        ]:
            Membership.objects.create(
                organization=self.org,
                user=user,
                role=role,
            )

        self.lead = Lead.objects.create(
            organization=self.org,
            title="Automation Opportunity",
            status=Lead.Status.QUALIFIED,
            created_by=self.owner,
            estimated_value="500000.00",
        )

        self.url = reverse(
            "lead-convert",
            kwargs={
                "organization_id": self.org.id,
                "pk": self.lead.id,
            },
        )

    def test_owner_can_convert_qualified_lead(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Opportunity.objects.count(), 1)

        opportunity = Opportunity.objects.get()

        self.assertEqual(
            opportunity.source_lead,
            self.lead,
        )
        self.assertEqual(
            opportunity.organization,
            self.org,
        )
        self.assertEqual(
            opportunity.status,
            Opportunity.Status.OPEN,
        )
        self.assertEqual(
            opportunity.converted_by,
            self.owner,
        )

    def test_manager_can_convert_qualified_lead(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 201)

    def test_sales_rep_cannot_convert(self):
        self.client.force_authenticate(user=self.sales_rep)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_convert(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)

    def test_unqualified_lead_is_rejected(self):
        self.lead.status = Lead.Status.NEW
        self.lead.save(update_fields=["status"])

        self.client.force_authenticate(user=self.owner)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Opportunity.objects.count(), 0)

    def test_archived_lead_is_rejected(self):
        self.lead.is_archived = True
        self.lead.save(update_fields=["is_archived"])

        self.client.force_authenticate(user=self.owner)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 400)

    def test_repeated_conversion_is_idempotent(self):
        self.client.force_authenticate(user=self.owner)

        first = self.client.post(self.url)
        second = self.client.post(self.url)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)

        self.assertEqual(
            first.data["id"],
            second.data["id"],
        )

        self.assertEqual(Opportunity.objects.count(), 1)

    def test_cross_tenant_conversion_is_rejected(self):
        foreign_lead = Lead.objects.create(
            organization=self.other_org,
            title="Private Opportunity",
            status=Lead.Status.QUALIFIED,
            created_by=self.outsider,
        )

        self.client.force_authenticate(user=self.owner)

        url = reverse(
            "lead-convert",
            kwargs={
                "organization_id": self.org.id,
                "pk": foreign_lead.id,
            },
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Opportunity.objects.count(), 0)

    def test_outsider_cannot_convert(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)

    def test_opportunity_listing_is_tenant_scoped(self):
        self.client.force_authenticate(user=self.owner)
        self.client.post(self.url)

        foreign_lead = Lead.objects.create(
            organization=self.other_org,
            title="Foreign Lead",
            created_by=self.outsider,
            status=Lead.Status.QUALIFIED,
        )

        Opportunity.objects.create(
            organization=self.other_org,
            source_lead=foreign_lead,
            title="Private Deal",
            converted_by=self.outsider,
        )

        response = self.client.get(
            reverse(
                "opportunity-list",
                kwargs={"organization_id": self.org.id},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_anonymous_conversion_is_rejected(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 401)