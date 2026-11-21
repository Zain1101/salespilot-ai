from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase

from apps.organizations.models import Membership
from apps.organizations.services import create_organization

from .models import Lead, LeadAssignmentHistory


User = get_user_model()


class LeadAssignmentTests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="assignment-owner@example.com",
            password="SecureTest@2026!",
        )

        self.manager = User.objects.create_user(
            email="assignment-manager@example.com",
            password="SecureTest@2026!",
        )

        self.sales_rep = User.objects.create_user(
            email="assignment-rep@example.com",
            password="SecureTest@2026!",
        )

        self.viewer = User.objects.create_user(
            email="assignment-viewer@example.com",
            password="SecureTest@2026!",
        )

        self.outsider = User.objects.create_user(
            email="assignment-outsider@example.com",
            password="SecureTest@2026!",
        )

        self.org = create_organization(
            name="Assignment Test Org",
            owner=self.owner,
        )

        self.other_org = create_organization(
            name="Other Assignment Org",
            owner=self.outsider,
        )

        self.manager_membership = Membership.objects.create(
            organization=self.org,
            user=self.manager,
            role=Membership.Role.MANAGER,
        )

        self.rep_membership = Membership.objects.create(
            organization=self.org,
            user=self.sales_rep,
            role=Membership.Role.SALES_REP,
        )

        Membership.objects.create(
            organization=self.org,
            user=self.viewer,
            role=Membership.Role.VIEWER,
        )

        self.lead = Lead.objects.create(
            organization=self.org,
            title="AI Sales Inquiry",
            created_by=self.owner,
        )

        self.url = reverse(
            "lead-assign",
            kwargs={
                "organization_id": self.org.id,
                "pk": self.lead.id,
            },
        )

        self.history_url = reverse(
            "lead-assignment-history",
            kwargs={
                "organization_id": self.org.id,
                "pk": self.lead.id,
            },
        )

    def test_owner_can_assign_lead(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {"assigned_to": str(self.rep_membership.id)},
        )

        self.assertEqual(response.status_code, 200)

        self.lead.refresh_from_db()
        self.assertEqual(
            self.lead.assigned_to,
            self.rep_membership,
        )

        self.assertEqual(
            LeadAssignmentHistory.objects.count(),
            1,
        )

    def test_manager_can_reassign_lead(self):
        self.lead.assigned_to = self.rep_membership
        self.lead.save(update_fields=["assigned_to"])

        self.client.force_authenticate(user=self.manager)

        response = self.client.post(
            self.url,
            {"assigned_to": str(self.manager_membership.id)},
        )

        self.assertEqual(response.status_code, 200)

        self.lead.refresh_from_db()
        self.assertEqual(
            self.lead.assigned_to,
            self.manager_membership,
        )

    def test_sales_rep_cannot_reassign(self):
        self.client.force_authenticate(user=self.sales_rep)

        response = self.client.post(
            self.url,
            {"assigned_to": str(self.rep_membership.id)},
        )

        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_assign_lead(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(
            self.url,
            {"assigned_to": str(self.rep_membership.id)},
        )

        self.assertEqual(response.status_code, 403)

    def test_foreign_membership_is_rejected(self):
        foreign_membership = Membership.objects.get(
            organization=self.other_org,
            user=self.outsider,
        )

        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {"assigned_to": str(foreign_membership.id)},
        )

        self.assertEqual(response.status_code, 400)

    def test_inactive_assignee_is_rejected(self):
        self.rep_membership.is_active = False
        self.rep_membership.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {"assigned_to": str(self.rep_membership.id)},
        )

        self.assertEqual(response.status_code, 400)

    def test_unassign_creates_history(self):
        self.lead.assigned_to = self.rep_membership
        self.lead.save(update_fields=["assigned_to"])

        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {"assigned_to": None},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.lead.refresh_from_db()
        self.assertIsNone(self.lead.assigned_to)

        event = LeadAssignmentHistory.objects.get()
        self.assertIsNone(event.new_assignee)

    def test_duplicate_assignment_creates_no_new_history(self):
        self.client.force_authenticate(user=self.owner)

        for _ in range(2):
            self.client.post(
                self.url,
                {"assigned_to": str(self.rep_membership.id)},
            )

        self.assertEqual(
            LeadAssignmentHistory.objects.count(),
            1,
        )

    def test_generic_patch_cannot_change_assignment(self):
        self.client.force_authenticate(user=self.owner)

        detail_url = reverse(
            "lead-detail",
            kwargs={
                "organization_id": self.org.id,
                "pk": self.lead.id,
            },
        )

        response = self.client.patch(
            detail_url,
            {"assigned_to": str(self.rep_membership.id)},
        )

        self.assertEqual(response.status_code, 400)

        self.lead.refresh_from_db()
        self.assertIsNone(self.lead.assigned_to)

    def test_outsider_cannot_assign_lead(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.post(
            self.url,
            {"assigned_to": str(self.rep_membership.id)},
        )

        self.assertEqual(response.status_code, 403)

    def test_assignment_history_is_readable(self):
        self.client.force_authenticate(user=self.owner)

        self.client.post(
            self.url,
            {"assigned_to": str(self.rep_membership.id)},
        )

        response = self.client.get(self.history_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_anonymous_user_cannot_assign(self):
        response = self.client.post(
            self.url,
            {"assigned_to": str(self.rep_membership.id)},
        )

        self.assertEqual(response.status_code, 401)