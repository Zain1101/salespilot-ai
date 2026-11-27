
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from apps.organizations.models import (
    Organization,
    Membership,
)

from apps.ai_assistant.tools.executor import (
    authorize_tool_context,
    execute_read_only_tool,
    ToolExecutionError,
)

from apps.ai_assistant.tools.registry import (
    ReadOnlyTool,
    registry,
)


User = get_user_model()


class ToolExecutorTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            email="tool-owner@example.com",
            password="TestPassword123!",
        )

        cls.outsider = User.objects.create_user(
            email="tool-outsider@example.com",
            password="TestPassword123!",
        )

        cls.organization = Organization.objects.create(
            name="Tool Test Organization",
            slug="tool-test-org",
            created_by=cls.owner,
        )

        cls.membership = Membership.objects.create(
            organization=cls.organization,
            user=cls.owner,
            role=Membership.Role.OWNER,
            is_active=True,
        )

    def test_valid_member_authorization(self):
        context = authorize_tool_context(
            user=self.owner,
            organization_id=self.organization.id,
        )

        self.assertEqual(
            context.organization.id,
            self.organization.id,
        )
        self.assertEqual(context.user, self.owner)

    def test_outsider_rejected(self):
        with self.assertRaises(PermissionDenied):
            authorize_tool_context(
                user=self.outsider,
                organization_id=self.organization.id,
            )

    def test_anonymous_rejected(self):
        with self.assertRaises(PermissionDenied):
            authorize_tool_context(
                user=None,
                organization_id=self.organization.id,
            )

    def test_inactive_membership_rejected(self):
        self.membership.is_active = False
        self.membership.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            authorize_tool_context(
                user=self.owner,
                organization_id=self.organization.id,
            )

    def test_inactive_organization_rejected(self):
        self.organization.is_active = False
        self.organization.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            authorize_tool_context(
                user=self.owner,
                organization_id=self.organization.id,
            )

    def test_unknown_tool_rejected(self):
        context = authorize_tool_context(
            user=self.owner,
            organization_id=self.organization.id,
        )

        with self.assertRaises(ToolExecutionError):
            execute_read_only_tool(
                tool_name="delete_everything",
                arguments={},
                context=context,
            )

    def test_reserved_organization_argument_rejected(self):
        context = authorize_tool_context(
            user=self.owner,
            organization_id=self.organization.id,
        )

        with self.assertRaises(ToolExecutionError):
            execute_read_only_tool(
                tool_name="anything",
                arguments={"organization_id": "other"},
                context=context,
            )

    def test_invalid_arguments_rejected(self):
        context = authorize_tool_context(
            user=self.owner,
            organization_id=self.organization.id,
        )

        with self.assertRaises(ToolExecutionError):
            execute_read_only_tool(
                tool_name="anything",
                arguments=["not", "an", "object"],
                context=context,
            )

    def test_invalid_context_rejected(self):
        with self.assertRaises(ToolExecutionError):
            execute_read_only_tool(
                tool_name="anything",
                arguments={},
                context=None,
            )

    def test_registered_tool_executes(self):
        context = authorize_tool_context(
            user=self.owner,
            organization_id=self.organization.id,
        )

        def sample_handler(*, context, arguments):
            return {
                "organization_id": str(
                    context.organization.id
                ),
                "message": arguments["message"],
            }

        tool = ReadOnlyTool(
            name="test_sample_tool",
            description="A harmless test tool",
            handler=sample_handler,
        )

        # Use an isolated registry copy during testing
        # so the global registry is not permanently changed.
        with patch.dict(registry._tools, {}, clear=True):
            registry.register(tool)

            result = execute_read_only_tool(
                tool_name="test_sample_tool",
                arguments={"message": "Hello"},
                context=context,
            )

        self.assertEqual(
            result["message"],
            "Hello",
        )

        self.assertEqual(
            result["organization_id"],
            str(self.organization.id),
        )
