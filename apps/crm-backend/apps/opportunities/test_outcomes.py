from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase

from apps.leads.models import Lead
from apps.organizations.models import Membership
from apps.organizations.services import create_organization
from apps.pipelines.services import create_sales_pipeline

from .models import Opportunity, OpportunityOutcomeHistory


User = get_user_model()


class OpportunityOutcomeTests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="outcome-owner@example.com",
            password="SecureTest@2026!",
        )

        self.manager = User.objects.create_user(
            email="outcome-manager@example.com",
            password="SecureTest@2026!",
        )

        self.rep = User.objects.create_user(
            email="outcome-rep@example.com",
            password="SecureTest@2026!",
        )

        self.viewer = User.objects.create_user(
            email="outcome-viewer@example.com",
            password="SecureTest@2026!",
        )

        self.outsider = User.objects.create_user(
            email="outcome-outsider@example.com",
            password="SecureTest@2026!",
        )

        self.org = create_organization(
            name="Outcome Test Org",
            owner=self.owner,
        )

        self.other_org = create_organization(
            name="Other Outcome Org",
            owner=self.outsider,
        )

        for user, role in [
            (self.manager, Membership.Role.MANAGER),
            (self.rep, Membership.Role.SALES_REP),
            (self.viewer, Membership.Role.VIEWER),
        ]:
            Membership.objects.create(
                organization=self.org,
                user=user,
                role=role,
            )

        self.pipeline = create_sales_pipeline(
            organization_id=self.org.id,
            created_by=self.owner,
            name="Test Sales Pipeline",
        )

        self.discovery = self.pipeline.stages.get(
            name="Discovery"
        )

        self.closing = self.pipeline.stages.get(
            name="Closing"
        )

        self.lead = Lead.objects.create(
            organization=self.org,
            title="Test Deal",
            created_by=self.owner,
            status=Lead.Status.QUALIFIED,
        )

        self.opportunity = Opportunity.objects.create(
            organization=self.org,
            source_lead=self.lead,
            title=self.lead.title,
            converted_by=self.owner,
            pipeline=self.pipeline,
            stage=self.discovery,
        )

        self.close_url = reverse(
            "opportunity-close",
            kwargs={
                "organization_id": self.org.id,
                "pk": self.opportunity.id,
            },
        )

        self.history_url = reverse(
            "opportunity-outcome-history",
            kwargs={
                "organization_id": self.org.id,
                "pk": self.opportunity.id,
            },
        )

    def test_won_requires_final_stage(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.close_url,
            {"outcome": "won", "actual_value": "500000.00"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            OpportunityOutcomeHistory.objects.count(), 0
        )

    def test_owner_can_mark_won(self):
        self.opportunity.stage = self.closing
        self.opportunity.save(update_fields=["stage"])

        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.close_url,
            {"outcome": "won", "actual_value": "475000.00"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["closed"])

        self.opportunity.refresh_from_db()
        self.assertEqual(
            self.opportunity.status,
            Opportunity.Status.WON,
        )
        self.assertIsNotNone(self.opportunity.closed_at)
        self.assertEqual(self.opportunity.closed_by, self.owner)
        self.assertEqual(
            str(self.opportunity.actual_value), "475000.00"
        )
        self.assertEqual(
            OpportunityOutcomeHistory.objects.count(), 1
        )

    def test_manager_can_mark_lost(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(
            self.close_url,
            {
                "outcome": "lost",
                "loss_reason": "Customer declined the proposal.",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.opportunity.refresh_from_db()
        self.assertEqual(
            self.opportunity.status,
            Opportunity.Status.LOST,
        )

    def test_lost_requires_reason(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.close_url,
            {"outcome": "lost"},
        )

        self.assertEqual(response.status_code, 400)

    def test_won_requires_actual_value(self):
        self.opportunity.stage = self.closing
        self.opportunity.save(update_fields=["stage"])

        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.close_url,
            {"outcome": "won"},
        )

        self.assertEqual(response.status_code, 400)

    def test_negative_actual_value_rejected(self):
        self.opportunity.stage = self.closing
        self.opportunity.save(update_fields=["stage"])

        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.close_url,
            {"outcome": "won", "actual_value": "-100.00"},
        )

        self.assertEqual(response.status_code, 400)

    def test_sales_rep_cannot_close_deal(self):
        self.client.force_authenticate(user=self.rep)

        response = self.client.post(
            self.close_url,
            {
                "outcome": "lost",
                "loss_reason": "No budget.",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_close_deal(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(
            self.close_url,
            {
                "outcome": "lost",
                "loss_reason": "No budget.",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_duplicate_closing_has_one_history_event(self):
        self.client.force_authenticate(user=self.owner)

        payload = {
            "outcome": "lost",
            "loss_reason": "Customer declined.",
        }

        first = self.client.post(self.close_url, payload)
        second = self.client.post(self.close_url, payload)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

        self.assertTrue(first.data["closed"])
        self.assertFalse(second.data["closed"])

        self.assertEqual(
            OpportunityOutcomeHistory.objects.count(), 1
        )

    def test_cannot_change_won_to_lost(self):
        self.opportunity.stage = self.closing
        self.opportunity.save(update_fields=["stage"])

        self.client.force_authenticate(user=self.owner)

        self.client.post(
            self.close_url,
            {"outcome": "won", "actual_value": "100000.00"},
        )

        response = self.client.post(
            self.close_url,
            {
                "outcome": "lost",
                "loss_reason": "Changed mind.",
            },
        )

        self.assertEqual(response.status_code, 400)

        self.opportunity.refresh_from_db()
        self.assertEqual(
            self.opportunity.status, Opportunity.Status.WON
        )

    def test_closed_deal_cannot_move_stage(self):
        self.client.force_authenticate(user=self.owner)

        self.client.post(
            self.close_url,
            {"outcome": "lost", "loss_reason": "No budget."},
        )

        move_url = reverse(
            "opportunity-move-stage",
            kwargs={
                "organization_id": self.org.id,
                "pk": self.opportunity.id,
            },
        )

        qualification = self.pipeline.stages.get(
            name="Qualification"
        )

        response = self.client.post(
            move_url,
            {"stage_id": str(qualification.id)},
        )

        self.assertEqual(response.status_code, 400)

    def test_viewer_can_read_history(self):
        self.client.force_authenticate(user=self.owner)

        self.client.post(
            self.close_url,
            {
                "outcome": "lost",
                "loss_reason": "Selected competitor.",
            },
        )

        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.history_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_outsider_cannot_close_deal(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.post(
            self.close_url,
            {
                "outcome": "lost",
                "loss_reason": "Not authorized.",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_anonymous_cannot_close_deal(self):
        response = self.client.post(
            self.close_url,
            {
                "outcome": "lost",
                "loss_reason": "No budget.",
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_cross_tenant_opportunity_rejected(self):
        foreign_lead = Lead.objects.create(
            organization=self.other_org,
            title="Other Organization Lead",
            created_by=self.outsider,
            status=Lead.Status.QUALIFIED,
        )

        foreign_pipeline = create_sales_pipeline(
            organization_id=self.other_org.id,
            created_by=self.outsider,
            name="Private Sales Pipeline",
        )

        foreign_opp = Opportunity.objects.create(
            organization=self.other_org,
            source_lead=foreign_lead,
            title="Private Deal",
            converted_by=self.outsider,
            pipeline=foreign_pipeline,
            stage=foreign_pipeline.stages.first(),
        )

        self.client.force_authenticate(user=self.owner)

        wrong_url = reverse(
            "opportunity-close",
            kwargs={
                "organization_id": self.org.id,
                "pk": foreign_opp.id,
            },
        )

        response = self.client.post(
            wrong_url,
            {
                "outcome": "lost",
                "loss_reason": "Unauthorized.",
            },
        )

        self.assertEqual(response.status_code, 400)