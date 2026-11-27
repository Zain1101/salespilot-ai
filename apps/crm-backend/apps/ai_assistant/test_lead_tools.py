
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.leads.models import Lead
from apps.organizations.models import (
    Organization,
    Membership,
)

from apps.ai_assistant.tools.executor import (
    authorize_tool_context,
    execute_read_only_tool,
)


User = get_user_model()


class LeadToolTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner_a = User.objects.create_user(
            email="lead-tool-a@example.com",
            password="TestPassword123!",
        )

        cls.owner_b = User.objects.create_user(
            email="lead-tool-b@example.com",
            password="TestPassword123!",
        )

        cls.org_a = Organization.objects.create(
            name="Lead Tool Tenant A",
            slug="lead-tool-a",
            created_by=cls.owner_a,
        )

        cls.org_b = Organization.objects.create(
            name="Lead Tool Tenant B",
            slug="lead-tool-b",
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
            status=Lead.Status.NEW,
        )

        cls.lead_b = Lead.objects.create(
            organization=cls.org_b,
            title="Confidential Tenant B Lead",
            created_by=cls.owner_b,
            status=Lead.Status.QUALIFIED,
        )

    def setUp(self):
        self.context = authorize_tool_context(
            user=self.owner_a,
            organization_id=self.org_a.id,
        )

    def run_tool(self, arguments):
        return execute_read_only_tool(
            tool_name="get_lead",
            arguments=arguments,
            context=self.context,
        )

    def test_can_retrieve_own_lead(self):
        result = self.run_tool({
            "lead_id": str(self.lead_a.id)
        })

        self.assertEqual(
            result["id"],
            str(self.lead_a.id),
        )

        self.assertEqual(
            result["title"],
            "Tenant A Lead",
        )

    def test_foreign_lead_is_inaccessible(self):
        result = self.run_tool({
            "lead_id": str(self.lead_b.id)
        })

        self.assertEqual(
            result["error"],
            "lead_not_found",
        )

        self.assertNotIn(
            "Confidential Tenant B Lead",
            str(result),
        )

    def test_nonexistent_lead(self):
        result = self.run_tool({
            "lead_id": str(uuid4())
        })

        self.assertEqual(
            result["error"],
            "lead_not_found",
        )

    def test_invalid_uuid(self):
        result = self.run_tool({
            "lead_id": "invalid-id"
        })

        self.assertEqual(
            result["error"],
            "invalid_lead_id",
        )

    def test_missing_arguments(self):
        result = self.run_tool({})

        self.assertEqual(
            result["error"],
            "invalid_arguments",
        )

    def test_extra_arguments(self):
        result = self.run_tool({
            "lead_id": str(self.lead_a.id),
            "status": "won",
        })

        self.assertEqual(
            result["error"],
            "invalid_arguments",
        )

    def test_unconverted_lead(self):
        result = self.run_tool({
            "lead_id": str(self.lead_a.id)
        })

        self.assertFalse(
            result["converted_to_opportunity"]
        )

        self.assertIsNone(
            result["opportunity_id"]
        )

    def test_does_not_modify_lead(self):
        original_status = self.lead_a.status

        self.run_tool({
            "lead_id": str(self.lead_a.id)
        })

        self.lead_a.refresh_from_db()

        self.assertEqual(
            self.lead_a.status,
            original_status,
        )
