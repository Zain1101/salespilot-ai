from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase

from apps.leads.models import Lead
from apps.opportunities.models import Opportunity
from apps.organizations.models import Membership
from apps.organizations.services import create_organization
from apps.pipelines.services import create_sales_pipeline


User = get_user_model()


class SalesAnalyticsTests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="analytics-owner@example.com",
            password="SecureTest@2026!",
        )

        self.viewer = User.objects.create_user(
            email="analytics-viewer@example.com",
            password="SecureTest@2026!",
        )

        self.outsider = User.objects.create_user(
            email="analytics-outsider@example.com",
            password="SecureTest@2026!",
        )

        self.org = create_organization(
            name="Analytics Test Organization",
            owner=self.owner,
        )

        self.other_org = create_organization(
            name="Analytics Private Organization",
            owner=self.outsider,
        )

        self.viewer_membership = Membership.objects.create(
            organization=self.org,
            user=self.viewer,
            role=Membership.Role.VIEWER,
        )

        self.pipeline = create_sales_pipeline(
            organization_id=self.org.id,
            created_by=self.owner,
            name="Sales Analytics Pipeline",
        )

        self.discovery = self.pipeline.stages.get(
            name="Discovery"
        )

        self.proposal = self.pipeline.stages.get(
            name="Proposal"
        )

        self.closing = self.pipeline.stages.get(
            name="Closing"
        )

        self.url = reverse(
            "analytics-overview",
            kwargs={"organization_id": self.org.id},
        )

        self.client.force_authenticate(user=self.owner)

    def create_deal(
        self,
        *,
        title,
        value,
        status=Opportunity.Status.OPEN,
        stage=None,
        actual_value=None,
        currency="PKR",
        organization=None,
        owner=None,
        pipeline=None,
    ):
        organization = organization or self.org
        owner = owner or self.owner
        pipeline = pipeline or self.pipeline
        stage = stage or self.discovery

        lead = Lead.objects.create(
            organization=organization,
            title=title,
            created_by=owner,
            status=Lead.Status.QUALIFIED,
        )

        return Opportunity.objects.create(
            organization=organization,
            source_lead=lead,
            title=title,
            converted_by=owner,
            pipeline=pipeline,
            stage=stage,
            estimated_value=Decimal(value),
            actual_value=(
                Decimal(actual_value)
                if actual_value is not None
                else None
            ),
            currency=currency,
            status=status,
        )

    def get_overview(self, currency="PKR"):
        return self.client.get(
            self.url,
            {"currency": currency},
        )

    def test_empty_analytics(self):
        response = self.get_overview()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["counts"]["total"], 0
        )
        self.assertEqual(
            response.data["revenue"]["won_revenue"],
            "0.00",
        )
        self.assertEqual(
            response.data["performance"]["win_rate_percentage"],
            "0.00",
        )

    def test_open_pipeline_value(self):
        self.create_deal(
            title="Discovery Deal",
            value="500000.00",
        )

        self.create_deal(
            title="Proposal Deal",
            value="200000.00",
            stage=self.proposal,
        )

        response = self.get_overview()

        self.assertEqual(
            response.data["counts"]["open"], 2
        )
        self.assertEqual(
            response.data["revenue"]["open_pipeline_value"],
            "700000.00",
        )

    def test_weighted_pipeline_forecast(self):
        # Discovery = 10%
        self.create_deal(
            title="Discovery Deal",
            value="500000.00",
        )

        # Proposal = 50%
        self.create_deal(
            title="Proposal Deal",
            value="200000.00",
            stage=self.proposal,
        )

        response = self.get_overview()

        # 500000 * 0.10 + 200000 * 0.50
        # = 150000
        self.assertEqual(
            response.data["revenue"]["weighted_open_value"],
            "150000.00",
        )

        self.assertEqual(
            len(response.data["stages"]), 2
        )

    def test_won_revenue_uses_actual_value(self):
        self.create_deal(
            title="Won Project",
            value="500000.00",
            actual_value="475000.00",
            status=Opportunity.Status.WON,
            stage=self.closing,
        )

        response = self.get_overview()

        self.assertEqual(
            response.data["revenue"]["won_revenue"],
            "475000.00",
        )

        self.assertEqual(
            response.data["revenue"]["open_pipeline_value"],
            "0.00",
        )

    def test_win_rate(self):
        self.create_deal(
            title="Won Deal",
            value="500000.00",
            actual_value="475000.00",
            status=Opportunity.Status.WON,
            stage=self.closing,
        )

        self.create_deal(
            title="Lost Deal",
            value="300000.00",
            status=Opportunity.Status.LOST,
        )

        response = self.get_overview()

        self.assertEqual(
            response.data["counts"]["closed"], 2
        )

        self.assertEqual(
            response.data["performance"]["win_rate_percentage"],
            "50.00",
        )

    def test_currency_isolation(self):
        self.create_deal(
            title="PKR Deal",
            value="500000.00",
            currency="PKR",
        )

        self.create_deal(
            title="USD Deal",
            value="10000.00",
            currency="USD",
        )

        pkr_response = self.get_overview("PKR")
        usd_response = self.get_overview("USD")

        self.assertEqual(
            pkr_response.data["revenue"]["open_pipeline_value"],
            "500000.00",
        )

        self.assertEqual(
            usd_response.data["revenue"]["open_pipeline_value"],
            "10000.00",
        )

        self.assertEqual(
            pkr_response.data["counts"]["total"], 1
        )
        self.assertEqual(
            usd_response.data["counts"]["total"], 1
        )

    def test_foreign_organization_not_included(self):
        foreign_pipeline = create_sales_pipeline(
            organization_id=self.other_org.id,
            created_by=self.outsider,
            name="Private Analytics Pipeline",
        )

        self.create_deal(
            title="Private Deal",
            value="900000.00",
            organization=self.other_org,
            owner=self.outsider,
            pipeline=foreign_pipeline,
            stage=foreign_pipeline.stages.first(),
        )

        self.create_deal(
            title="Our Deal",
            value="100000.00",
        )

        response = self.get_overview()

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.data["counts"]["total"], 1
        )

        self.assertEqual(
            response.data["revenue"]["open_pipeline_value"],
            "100000.00",
        )

    def test_viewer_can_read_analytics(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.get_overview()

        self.assertEqual(response.status_code, 200)

    def test_inactive_member_cannot_read(self):
        self.viewer_membership.is_active = False
        self.viewer_membership.save(
            update_fields=["is_active"]
        )

        self.client.force_authenticate(user=self.viewer)

        response = self.get_overview()

        self.assertEqual(response.status_code, 403)

    def test_outsider_cannot_read_analytics(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.get_overview()

        self.assertEqual(response.status_code, 403)

    def test_invalid_currency_rejected(self):
        response = self.get_overview("GBP")

        self.assertEqual(response.status_code, 400)

    def test_currency_is_required(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 400)

    def test_anonymous_access_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.get_overview()

        self.assertEqual(response.status_code, 401)

    def test_post_not_allowed(self):
        response = self.client.post(
            self.url,
            {"currency": "PKR"},
        )

        self.assertEqual(response.status_code, 405)