from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase

from apps.activities.models import Activity
from apps.leads.models import Lead, LeadStatusHistory
from apps.organizations.models import Membership
from apps.organizations.services import create_organization
from apps.pipelines.services import create_sales_pipeline
from apps.tasks.models import (
    SalesTask,
    SalesTaskStatusHistory,
)

from .models import (
    Opportunity,
    OpportunityStageHistory,
    OpportunityOutcomeHistory,
)


User = get_user_model()


class OpportunityTimelineTests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="timeline-owner@example.com",
            password="SecureTest@2026!",
        )

        self.viewer = User.objects.create_user(
            email="timeline-viewer@example.com",
            password="SecureTest@2026!",
        )

        self.outsider = User.objects.create_user(
            email="timeline-outsider@example.com",
            password="SecureTest@2026!",
        )

        self.org = create_organization(
            name="Timeline Test Organization",
            owner=self.owner,
        )

        self.other_org = create_organization(
            name="Private Timeline Organization",
            owner=self.outsider,
        )

        self.viewer_membership = Membership.objects.create(
            organization=self.org,
            user=self.viewer,
            role=Membership.Role.VIEWER,
        )

        self.owner_membership = Membership.objects.get(
            organization=self.org,
            user=self.owner,
        )

        self.pipeline = create_sales_pipeline(
            organization_id=self.org.id,
            created_by=self.owner,
            name="Timeline Pipeline",
        )

        self.discovery = self.pipeline.stages.get(
            name="Discovery"
        )

        self.qualification = self.pipeline.stages.get(
            name="Qualification"
        )

        self.lead = Lead.objects.create(
            organization=self.org,
            title="Timeline Test Lead",
            created_by=self.owner,
            status=Lead.Status.QUALIFIED,
        )

        self.opportunity = Opportunity.objects.create(
            organization=self.org,
            source_lead=self.lead,
            title="Timeline Test Opportunity",
            converted_by=self.owner,
            pipeline=self.pipeline,
            stage=self.discovery,
        )

        self.url = reverse(
            "opportunity-timeline",
            kwargs={
                "organization_id": self.org.id,
                "pk": self.opportunity.id,
            },
        )

        self.client.force_authenticate(user=self.owner)

    def create_activity(self, subject, lead=None):
        return Activity.objects.create(
            organization=self.org,
            activity_type=Activity.Type.CALL,
            subject=subject,
            created_by=self.owner,
            **(
                {"lead": lead}
                if lead is not None
                else {"opportunity": self.opportunity}
            ),
        )

    def create_task(self):
        return SalesTask.objects.create(
            organization=self.org,
            title="Follow up with customer",
            assigned_to=self.owner_membership,
            created_by=self.owner,
            opportunity=self.opportunity,
            due_at=timezone.now() + timedelta(days=1),
        )

    def test_empty_timeline(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["events"], [])
        self.assertFalse(response.data["has_more"])

    def test_opportunity_activity_appears(self):
        self.create_activity("Customer discussion")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["events"]), 1)
        self.assertEqual(
            response.data["events"][0]["event_type"],
            "activity",
        )

    def test_original_lead_activity_appears(self):
        self.create_activity(
            "Early qualification call",
            lead=self.lead,
        )

        response = self.client.get(self.url)

        self.assertEqual(len(response.data["events"]), 1)
        self.assertEqual(
            response.data["events"][0]["title"],
            "Early qualification call",
        )

    def test_task_creation_and_completion_appear(self):
        task = self.create_task()

        SalesTaskStatusHistory.objects.create(
            organization=self.org,
            task=task,
            old_status=SalesTask.Status.PENDING,
            new_status=SalesTask.Status.COMPLETED,
            changed_by=self.owner,
        )

        response = self.client.get(self.url)

        types = {
            event["event_type"]
            for event in response.data["events"]
        }

        self.assertIn("task_created", types)
        self.assertIn("task_status", types)

    def test_stage_and_outcome_events_appear(self):
        OpportunityStageHistory.objects.create(
            organization=self.org,
            opportunity=self.opportunity,
            old_stage=self.discovery,
            new_stage=self.qualification,
            changed_by=self.owner,
        )

        OpportunityOutcomeHistory.objects.create(
            organization=self.org,
            opportunity=self.opportunity,
            old_status=Opportunity.Status.OPEN,
            new_status=Opportunity.Status.LOST,
            changed_by=self.owner,
            loss_reason="Customer declined.",
        )

        response = self.client.get(self.url)

        types = {
            event["event_type"]
            for event in response.data["events"]
        }

        self.assertIn("stage_changed", types)
        self.assertIn("deal_outcome", types)

    def test_lead_qualification_history_appears(self):
        LeadStatusHistory.objects.create(
            organization=self.org,
            lead=self.lead,
            old_status=Lead.Status.CONTACTED,
            new_status=Lead.Status.QUALIFIED,
            changed_by=self.owner,
            reason="Budget and requirements confirmed.",
        )

        response = self.client.get(self.url)

        self.assertEqual(
            response.data["events"][0]["event_type"],
            "lead_status",
        )

    def test_limit_and_has_more(self):
        for index in range(5):
            self.create_activity(f"Call {index}")

        response = self.client.get(
            self.url,
            {"limit": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["events"]), 2)
        self.assertTrue(response.data["has_more"])

    def test_invalid_limit_rejected(self):
        response = self.client.get(
            self.url,
            {"limit": 500},
        )

        self.assertEqual(response.status_code, 400)

    def test_viewer_can_read_timeline(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_inactive_member_cannot_read(self):
        self.viewer_membership.is_active = False
        self.viewer_membership.save(
            update_fields=["is_active"]
        )

        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_outsider_cannot_read(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_foreign_opportunity_hidden(self):
        foreign_pipeline = create_sales_pipeline(
            organization_id=self.other_org.id,
            created_by=self.outsider,
            name="Private Timeline Pipeline",
        )

        foreign_lead = Lead.objects.create(
            organization=self.other_org,
            title="Private Lead",
            created_by=self.outsider,
        )

        foreign_opportunity = Opportunity.objects.create(
            organization=self.other_org,
            source_lead=foreign_lead,
            title="Private Opportunity",
            converted_by=self.outsider,
            pipeline=foreign_pipeline,
            stage=foreign_pipeline.stages.first(),
        )

        foreign_url = reverse(
            "opportunity-timeline",
            kwargs={
                "organization_id": self.org.id,
                "pk": foreign_opportunity.id,
            },
        )

        response = self.client.get(foreign_url)

        self.assertEqual(response.status_code, 404)

    def test_anonymous_access_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)