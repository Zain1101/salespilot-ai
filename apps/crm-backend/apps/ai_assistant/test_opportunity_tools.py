
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.leads.models import Lead
from apps.opportunities.models import Opportunity
from apps.organizations.models import (
    Organization,
    Membership,
)

from apps.ai_assistant.tools.executor import (
    authorize_tool_context,
    execute_read_only_tool,
)


User = get_user_model()


class OpportunityToolTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_a = User.objects.create_user(
            email="opportunity-tool-a@example.com",
            password="TestPassword123!",
        )

        cls.owner_b = User.objects.create_user(
            email="opportunity-tool-b@example.com",
            password="TestPassword123!",
        )

        cls.org_a = Organization.objects.create(
            name="Opportunity Tool Tenant A",
            slug="opportunity-tool-a",
            created_by=cls.owner_a,
        )

        cls.org_b = Organization.objects.create(
            name="Opportunity Tool Tenant B",
            slug="opportunity-tool-b",
            created_by=cls.owner_b,
        )

        Membership.objects.create(
            organization=cls.org_a,
            user=cls.owner_a,
            role=Membership.Role.OWNER,
            is_active=True,
        )

        Membership.objects.create(
            organization=cls.org_b,
            user=cls.owner_b,
            role=Membership.Role.OWNER,
            is_active=True,
        )

        cls.lead_a = Lead.objects.create(
            organization=cls.org_a,
            title="Tenant A Lead",
            created_by=cls.owner_a,
            status=Lead.Status.QUALIFIED,
        )

        cls.lead_b = Lead.objects.create(
            organization=cls.org_b,
            title="Tenant B Lead",
            created_by=cls.owner_b,
            status=Lead.Status.QUALIFIED,
        )

        cls.opportunity_a = Opportunity.objects.create(
            organization=cls.org_a,
            source_lead=cls.lead_a,
            title="Tenant A Opportunity",
            converted_by=cls.owner_a,
            estimated_value="150000.00",
            currency="PKR",
        )

        cls.opportunity_b = Opportunity.objects.create(
            organization=cls.org_b,
            source_lead=cls.lead_b,
            title="Confidential Tenant B Opportunity",
            converted_by=cls.owner_b,
            estimated_value="750000.00",
            currency="PKR",
        )

    def setUp(self):
        self.context_a = authorize_tool_context(
            user=self.owner_a,
            organization_id=self.org_a.id,
        )

    def run_tool(self, arguments):
        return execute_read_only_tool(
            tool_name="get_opportunity",
            arguments=arguments,
            context=self.context_a,
        )

    def test_can_retrieve_own_opportunity(self):
        result = self.run_tool({
            "opportunity_id": str(
                self.opportunity_a.id
            )
        })

        self.assertEqual(
            result["id"],
            str(self.opportunity_a.id),
        )

        self.assertEqual(
            result["title"],
            "Tenant A Opportunity",
        )

    def test_foreign_opportunity_not_found(self):
        result = self.run_tool({
            "opportunity_id": str(
                self.opportunity_b.id
            )
        })

        self.assertEqual(
            result["error"],
            "opportunity_not_found",
        )

        self.assertNotIn(
            "Confidential Tenant B Opportunity",
            str(result),
        )

    def test_nonexistent_opportunity(self):
        result = self.run_tool({
            "opportunity_id": str(uuid4())
        })

        self.assertEqual(
            result["error"],
            "opportunity_not_found",
        )

    def test_invalid_uuid(self):
        result = self.run_tool({
            "opportunity_id": "not-a-uuid"
        })

        self.assertEqual(
            result["error"],
            "invalid_opportunity_id",
        )

    def test_missing_argument(self):
        result = self.run_tool({})

        self.assertEqual(
            result["error"],
            "invalid_arguments",
        )

    def test_extra_argument_rejected(self):
        result = self.run_tool({
            "opportunity_id": str(
                self.opportunity_a.id
            ),
            "unexpected": "value",
        })

        self.assertEqual(
            result["error"],
            "invalid_arguments",
        )

    
    def test_does_not_modify_opportunity(self):
        from decimal import Decimal

        original_status = self.opportunity_a.status
        original_value = Decimal(
            str(self.opportunity_a.estimated_value)
        )

        result = self.run_tool({
            "opportunity_id": str(self.opportunity_a.id)
        })

        self.assertEqual(
            result["id"],
            str(self.opportunity_a.id),
        )

        self.opportunity_a.refresh_from_db()

        self.assertEqual(
            self.opportunity_a.status,
            original_status,
        )

        self.assertEqual(
            self.opportunity_a.estimated_value,
            original_value,
        )
