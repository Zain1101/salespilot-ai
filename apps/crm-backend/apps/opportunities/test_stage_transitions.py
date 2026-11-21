from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase

from apps.leads.models import Lead
from apps.organizations.models import Membership
from apps.organizations.services import create_organization
from apps.pipelines.models import PipelineStage
from apps.pipelines.services import create_sales_pipeline

from .models import Opportunity, OpportunityStageHistory


User = get_user_model()


class OpportunityStageTests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="stage-owner@example.com",
            password="SecureTest@2026!",
        )

        self.viewer = User.objects.create_user(
            email="stage-viewer@example.com",
            password="SecureTest@2026!",
        )

        self.outsider = User.objects.create_user(
            email="stage-outsider@example.com",
            password="SecureTest@2026!",
        )

        self.org = create_organization(
            name="Stage Testing",
            owner=self.owner,
        )

        self.other_org = create_organization(
            name="Another Stage Organization",
            owner=self.outsider,
        )

        Membership.objects.create(
            organization=self.org,
            user=self.viewer,
            role=Membership.Role.VIEWER,
        )

        self.pipeline = create_sales_pipeline(
            organization_id=self.org.id,
            created_by=self.owner,
            name="Sales Pipeline",
        )

        self.discovery = self.pipeline.stages.get(
            name="Discovery"
        )

        self.qualification = self.pipeline.stages.get(
            name="Qualification"
        )

        self.closing = self.pipeline.stages.get(
            name="Closing"
        )

        self.lead = Lead.objects.create(
            organization=self.org,
            title="AI Sales Automation",
            status=Lead.Status.QUALIFIED,
            created_by=self.owner,
        )

        self.opportunity = Opportunity.objects.create(
            organization=self.org,
            source_lead=self.lead,
            title=self.lead.title,
            converted_by=self.owner,
            pipeline=self.pipeline,
            stage=self.discovery,
        )

        self.url = reverse(
            "opportunity-move-stage",
            kwargs={
                "organization_id": self.org.id,
                "pk": self.opportunity.id,
            },
        )

        self.history_url = reverse(
            "opportunity-stage-history",
            kwargs={
                "organization_id": self.org.id,
                "pk": self.opportunity.id,
            },
        )

    def test_owner_can_move_forward(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {"stage_id": str(self.qualification.id)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["moved"])

        self.opportunity.refresh_from_db()

        self.assertEqual(
            self.opportunity.stage,
            self.qualification,
        )

        self.assertEqual(
            OpportunityStageHistory.objects.count(),
            1,
        )

    def test_owner_can_move_backward(self):
        self.opportunity.stage = self.qualification
        self.opportunity.save(update_fields=["stage"])

        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {"stage_id": str(self.discovery.id)},
        )

        self.assertEqual(response.status_code, 200)

    def test_skipping_stages_is_rejected(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {"stage_id": str(self.closing.id)},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            OpportunityStageHistory.objects.count(),
            0,
        )

    def test_duplicate_movement_is_no_op(self):
        self.client.force_authenticate(user=self.owner)

        self.client.post(
            self.url,
            {"stage_id": str(self.qualification.id)},
        )

        response = self.client.post(
            self.url,
            {"stage_id": str(self.qualification.id)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["moved"])

        self.assertEqual(
            OpportunityStageHistory.objects.count(),
            1,
        )

    def test_viewer_cannot_move_opportunity(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(
            self.url,
            {"stage_id": str(self.qualification.id)},
        )

        self.assertEqual(response.status_code, 403)

    def test_viewer_can_read_history(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.history_url)

        self.assertEqual(response.status_code, 200)

    def test_foreign_pipeline_stage_is_rejected(self):
        foreign_pipeline = create_sales_pipeline(
            organization_id=self.other_org.id,
            created_by=self.outsider,
            name="Private Pipeline",
        )

        foreign_stage = foreign_pipeline.stages.first()

        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {"stage_id": str(foreign_stage.id)},
        )

        self.assertEqual(response.status_code, 400)

    def test_closed_opportunity_cannot_move(self):
        self.opportunity.status = Opportunity.Status.WON
        self.opportunity.save(update_fields=["status"])

        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {"stage_id": str(self.qualification.id)},
        )

        self.assertEqual(response.status_code, 400)

    def test_inactive_membership_cannot_move(self):
        Membership.objects.filter(
            organization=self.org,
            user=self.viewer,
        ).update(is_active=False)

        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(
            self.url,
            {"stage_id": str(self.qualification.id)},
        )

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_cannot_move(self):
        response = self.client.post(
            self.url,
            {"stage_id": str(self.qualification.id)},
        )

        self.assertEqual(response.status_code, 401)