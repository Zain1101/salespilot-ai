from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase

from apps.leads.models import Lead
from apps.organizations.services import create_organization
from apps.pipelines.services import create_sales_pipeline

from .models import Opportunity


User = get_user_model()


class OpportunityPipelineTests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="pipeline-integration-owner@example.com",
            password="SecureTest@2026!",
        )

        self.organization = create_organization(
            name="Pipeline Integration Agency",
            owner=self.owner,
        )

        self.pipeline = create_sales_pipeline(
            organization_id=self.organization.id,
            created_by=self.owner,
            name="Default Sales Pipeline",
        )

        self.lead = Lead.objects.create(
            organization=self.organization,
            title="AI Automation Opportunity",
            status=Lead.Status.QUALIFIED,
            created_by=self.owner,
            estimated_value="500000.00",
        )

        self.url = reverse(
            "lead-convert",
            kwargs={
                "organization_id": self.organization.id,
                "pk": self.lead.id,
            },
        )

        self.client.force_authenticate(user=self.owner)

    def test_conversion_assigns_default_pipeline(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 201)

        opportunity = Opportunity.objects.get(
            source_lead=self.lead
        )

        self.assertEqual(
            opportunity.pipeline,
            self.pipeline,
        )

        self.assertEqual(
            opportunity.stage.name,
            "Discovery",
        )

        self.assertEqual(
            opportunity.stage.position,
            1,
        )

    def test_conversion_uses_first_stage(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["stage_name"],
            "Discovery",
        )
        self.assertEqual(
            response.data["stage_probability"],
            10,
        )

    def test_missing_default_pipeline_rejected(self):
        self.pipeline.is_default = False
        self.pipeline.save(update_fields=["is_default"])

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            Opportunity.objects.count(),
            0,
        )

    def test_repeat_conversion_preserves_pipeline(self):
        first = self.client.post(self.url)
        second = self.client.post(self.url)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)

        self.assertEqual(
            first.data["id"],
            second.data["id"],
        )

        self.assertEqual(
            first.data["pipeline"],
            second.data["pipeline"],
        )

        self.assertEqual(
            Opportunity.objects.count(),
            1,
        )