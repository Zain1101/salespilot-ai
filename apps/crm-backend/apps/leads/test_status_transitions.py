from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase

from apps.organizations.models import Membership
from apps.organizations.services import create_organization

from .models import Lead, LeadStatusHistory


User = get_user_model()


class LeadStatusTransitionTests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="lead-owner@example.com",
            password="SecureTest@2026!",
        )

        self.viewer = User.objects.create_user(
            email="lead-viewer@example.com",
            password="SecureTest@2026!",
        )

        self.outsider = User.objects.create_user(
            email="lead-outsider@example.com",
            password="SecureTest@2026!",
        )

        self.org = create_organization(
            name="Lead Workflow Organization",
            owner=self.owner,
        )

        self.other_org = create_organization(
            name="Another Organization",
            owner=self.outsider,
        )

        self.viewer_membership = Membership.objects.create(
            organization=self.org,
            user=self.viewer,
            role=Membership.Role.VIEWER,
        )

        self.lead = Lead.objects.create(
            organization=self.org,
            title="AI Automation Inquiry",
            created_by=self.owner,
        )

        self.other_lead = Lead.objects.create(
            organization=self.other_org,
            title="Private Lead",
            created_by=self.outsider,
        )

        self.transition_url = reverse(
            "lead-transition",
            kwargs={
                "organization_id": self.org.id,
                "pk": self.lead.id,
            },
        )

        self.history_url = reverse(
            "lead-status-history",
            kwargs={
                "organization_id": self.org.id,
                "pk": self.lead.id,
            },
        )

    def test_new_to_contacted(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.transition_url,
            {
                "status": "contacted",
                "reason": "Initial call completed.",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.lead.refresh_from_db()
        self.assertEqual(
            self.lead.status,
            Lead.Status.CONTACTED,
        )

        self.assertEqual(
            LeadStatusHistory.objects.count(), 1
        )

    def test_contacted_to_qualified(self):
        self.lead.status = Lead.Status.CONTACTED
        self.lead.save(update_fields=["status"])

        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.transition_url,
            {
                "status": "qualified",
                "reason": "Budget confirmed.",
            },
        )

        self.assertEqual(response.status_code, 200)

    def test_invalid_transition_is_rejected(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.transition_url,
            {"status": "qualified"},
        )

        self.assertEqual(response.status_code, 400)

        self.lead.refresh_from_db()
        self.assertEqual(
            self.lead.status,
            Lead.Status.NEW,
        )

    def test_disqualification_requires_reason(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.transition_url,
            {"status": "disqualified"},
        )

        self.assertEqual(response.status_code, 400)

    def test_repeated_transition_does_not_duplicate_history(self):
        self.client.force_authenticate(user=self.owner)

        for _ in range(2):
            self.client.post(
                self.transition_url,
                {"status": "contacted"},
            )

        self.assertEqual(
            LeadStatusHistory.objects.count(), 1
        )

    def test_viewer_cannot_change_status(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(
            self.transition_url,
            {"status": "contacted"},
        )

        self.assertEqual(response.status_code, 403)

    def test_outsider_cannot_change_status(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.post(
            self.transition_url,
            {"status": "contacted"},
        )

        self.assertEqual(response.status_code, 403)

    def test_cross_tenant_lead_is_not_modified(self):
        self.client.force_authenticate(user=self.owner)

        url = reverse(
            "lead-transition",
            kwargs={
                "organization_id": self.org.id,
                "pk": self.other_lead.id,
            },
        )

        response = self.client.post(
            url,
            {"status": "contacted"},
        )

        self.assertEqual(response.status_code, 400)

        self.other_lead.refresh_from_db()
        self.assertEqual(
            self.other_lead.status,
            Lead.Status.NEW,
        )

    def test_archived_lead_cannot_change_status(self):
        self.lead.is_archived = True
        self.lead.save(update_fields=["is_archived"])

        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.transition_url,
            {"status": "contacted"},
        )

        self.assertEqual(response.status_code, 400)

    def test_status_history_is_accessible(self):
        self.client.force_authenticate(user=self.owner)

        self.client.post(
            self.transition_url,
            {
                "status": "contacted",
                "reason": "Customer called.",
            },
        )

        response = self.client.get(self.history_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        self.assertEqual(
            response.data[0]["new_status"],
            "contacted",
        )

    def test_viewer_can_read_status_history(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.history_url)

        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_user_is_rejected(self):
        response = self.client.post(
            self.transition_url,
            {"status": "contacted"},
        )

        self.assertEqual(response.status_code, 401)