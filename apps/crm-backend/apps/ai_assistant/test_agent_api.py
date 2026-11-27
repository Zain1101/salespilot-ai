
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from apps.organizations.models import (
    Organization,
    Membership,
)

from apps.ai_assistant.agent import AgentError
from unittest.mock import patch
from rest_framework.throttling import ScopedRateThrottle

User = get_user_model()


class SalesAgentAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            email="agent-api-owner@example.com",
            password="TestPassword123!",
        )

        cls.outsider = User.objects.create_user(
            email="agent-api-outsider@example.com",
            password="TestPassword123!",
        )

        cls.organization = Organization.objects.create(
            name="Agent API Test Organization",
            slug="agent-api-test-org",
            created_by=cls.owner,
        )

        cls.other_organization = Organization.objects.create(
            name="Other Agent Organization",
            slug="other-agent-org",
            created_by=cls.outsider,
        )

        Membership.objects.create(
            organization=cls.organization,
            user=cls.owner,
            role=Membership.Role.OWNER,
            is_active=True,
        )

        Membership.objects.create(
            organization=cls.other_organization,
            user=cls.outsider,
            role=Membership.Role.OWNER,
            is_active=True,
        )

        cls.url = reverse(
            "ai-sales-agent",
            kwargs={
                "organization_id": cls.organization.id,
            },
        )

    def setUp(self):
        cache.clear()

        self.client.force_authenticate(
            user=self.owner
        )

    @patch("apps.ai_assistant.views.run_sales_agent")
    def test_valid_request(self, mock_agent):
        mock_agent.return_value = {
            "answer": "Call the overdue customer first.",
            "tools_used": ["list_my_tasks"],
            "read_only": True,
        }

        response = self.client.post(
            self.url,
            {
                "question": "Show my overdue tasks.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["tools_used"],
            ["list_my_tasks"],
        )

        self.assertTrue(
            response.data["read_only"]
        )

        mock_agent.assert_called_once_with(
            user=self.owner,
            organization_id=self.organization.id,
            question="Show my overdue tasks.",
        )

    @patch("apps.ai_assistant.views.run_sales_agent")
    def test_unauthenticated_request(self, mock_agent):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.url,
            {"question": "Show tasks"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        mock_agent.assert_not_called()

    @patch("apps.ai_assistant.views.run_sales_agent")
    def test_cross_tenant_request(self, mock_agent):
        self.client.force_authenticate(
            user=self.outsider
        )

        response = self.client.post(
            self.url,
            {"question": "Show tasks"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        mock_agent.assert_not_called()

    @patch("apps.ai_assistant.views.run_sales_agent")
    def test_missing_question(self, mock_agent):
        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        mock_agent.assert_not_called()

    @patch("apps.ai_assistant.views.run_sales_agent")
    def test_empty_question(self, mock_agent):
        response = self.client.post(
            self.url,
            {"question": "   "},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        mock_agent.assert_not_called()

    @patch("apps.ai_assistant.views.run_sales_agent")
    def test_question_too_long(self, mock_agent):
        response = self.client.post(
            self.url,
            {"question": "A" * 1001},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        mock_agent.assert_not_called()

    @patch("apps.ai_assistant.views.run_sales_agent")
    def test_agent_failure(self, mock_agent):
        mock_agent.side_effect = AgentError(
            "AI provider request failed."
        )

        response = self.client.post(
            self.url,
            {"question": "Analyze my leads"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

        self.assertNotIn(
            "AI provider request failed",
            str(response.data),
        )


    
    @patch("apps.ai_assistant.views.run_sales_agent")
    def test_rate_limit(self, mock_agent):
        mock_agent.return_value = {
            "answer": "No overdue tasks.",
            "tools_used": ["list_my_tasks"],
            "read_only": True,
        }

        payload = {
            "question": "Show my tasks"
        }

        # Patch the throttle's actual rate configuration.
        # This avoids relying on settings reloading.
        with patch.dict(
            ScopedRateThrottle.THROTTLE_RATES,
            {"ai_agent": "2/min"},
        ):
            cache.clear()

            first = self.client.post(
                self.url,
                payload,
                format="json",
            )

            second = self.client.post(
                self.url,
                payload,
                format="json",
            )

            third = self.client.post(
                self.url,
                payload,
                format="json",
            )

        self.assertEqual(
            first.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            second.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            third.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

        self.assertEqual(
            mock_agent.call_count,
            2,
        )
