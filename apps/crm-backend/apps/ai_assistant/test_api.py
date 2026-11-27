
from unittest.mock import patch
from types import SimpleNamespace
from uuid import uuid4

from django.http import Http404
from django.test import SimpleTestCase

from rest_framework.test import (
    APIRequestFactory,
    force_authenticate,
)

from apps.ai_assistant.views import OpportunityAIAnalysisView
from apps.ai_assistant.llm import AIProviderError
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.organizations.models import Organization, Membership
from apps.opportunities.models import Opportunity


User = get_user_model()


class OpportunityAIAPITests(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = OpportunityAIAnalysisView.as_view()

        self.organization_id = uuid4()
        self.opportunity_id = uuid4()

        self.user = SimpleNamespace(
            pk=1,
            is_authenticated=True,
            is_active=True,
        )

        self.context = {
            "opportunity": {
                "id": str(self.opportunity_id),
                "title": "Demo Sales Opportunity",
                "status": "won",
                "currency": "PKR",
                "actual_value": "475000.00",
            },
            "recent_events": [],
            "timeline_has_more": False,
            "context_read_only": True,
        }

        self.analysis = {
            "answer": (
                "The opportunity is Won. "
                "Recommend post-sale follow-up."
            ),
            "model": "test-model",
        }

    def make_request(self, data=None, user=None):
        request = self.factory.post(
            "/api/test/analyze/",
            {} if data is None else data,
            format="json",
        )

        if user is not None:
            force_authenticate(request, user=user)

        return request

    def call_view(self, request):
        return self.view(
            request,
            organization_id=self.organization_id,
            pk=self.opportunity_id,
        )

    @patch(
        "apps.ai_assistant.views.generate_sales_analysis"
    )
    @patch(
        "apps.ai_assistant.views.build_opportunity_context"
    )
    @patch(
        "common.tenancy.permissions.IsTenantMember.has_permission",
        return_value=True,
    )
    def test_successful_analysis(
        self, mock_permission, mock_context, mock_llm
    ):
        mock_context.return_value = self.context
        mock_llm.return_value = self.analysis

        response = self.call_view(
            self.make_request(
                {"question": "Analyze this deal."},
                user=self.user,
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["read_only"])
        self.assertEqual(
            response.data["model"],
            "test-model",
        )

        mock_context.assert_called_once()
        mock_llm.assert_called_once()

    @patch(
        "apps.ai_assistant.views.generate_sales_analysis"
    )
    @patch(
        "apps.ai_assistant.views.build_opportunity_context"
    )
    @patch(
        "common.tenancy.permissions.IsTenantMember.has_permission",
        return_value=True,
    )
    def test_default_question(
        self, mock_permission, mock_context, mock_llm
    ):
        mock_context.return_value = self.context
        mock_llm.return_value = self.analysis

        response = self.call_view(
            self.make_request(user=self.user)
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Analyze this opportunity",
            mock_llm.call_args.kwargs["question"],
        )

    @patch(
        "apps.ai_assistant.views.generate_sales_analysis"
    )
    @patch(
        "common.tenancy.permissions.IsTenantMember.has_permission",
        return_value=True,
    )
    def test_empty_question_rejected(
        self, mock_permission, mock_llm
    ):
        response = self.call_view(
            self.make_request(
                {"question": ""},
                user=self.user,
            )
        )

        self.assertEqual(response.status_code, 400)
        mock_llm.assert_not_called()

    @patch(
        "apps.ai_assistant.views.generate_sales_analysis"
    )
    @patch(
        "common.tenancy.permissions.IsTenantMember.has_permission",
        return_value=True,
    )
    def test_long_question_rejected(
        self, mock_permission, mock_llm
    ):
        response = self.call_view(
            self.make_request(
                {"question": "A" * 1001},
                user=self.user,
            )
        )

        self.assertEqual(response.status_code, 400)
        mock_llm.assert_not_called()

    @patch(
        "apps.ai_assistant.views.generate_sales_analysis"
    )
    def test_unauthenticated_request(self, mock_llm):
        response = self.call_view(
            self.make_request()
        )

        self.assertIn(response.status_code, [401, 403])
        mock_llm.assert_not_called()

    @patch(
        "apps.ai_assistant.views.generate_sales_analysis"
    )
    @patch(
        "apps.ai_assistant.views.build_opportunity_context"
    )
    @patch(
        "common.tenancy.permissions.IsTenantMember.has_permission",
        return_value=True,
    )
    def test_provider_failure(
        self, mock_permission, mock_context, mock_llm
    ):
        mock_context.return_value = self.context
        mock_llm.side_effect = AIProviderError(
            "Provider failure"
        )

        response = self.call_view(
            self.make_request(user=self.user)
        )

        self.assertEqual(response.status_code, 503)
        self.assertNotIn(
            "Provider failure",
            str(response.data),
        )

    @patch(
        "apps.ai_assistant.views.generate_sales_analysis"
    )
    @patch(
        "apps.ai_assistant.views.build_opportunity_context"
    )
    @patch(
        "common.tenancy.permissions.IsTenantMember.has_permission",
        return_value=True,
    )
    def test_missing_opportunity(
        self, mock_permission, mock_context, mock_llm
    ):
        mock_context.side_effect = Http404()

        response = self.call_view(
            self.make_request(user=self.user)
        )

        self.assertEqual(response.status_code, 404)
        mock_llm.assert_not_called()

    @patch(
        "apps.ai_assistant.views.generate_sales_analysis"
    )
    @patch(
        "apps.ai_assistant.views.build_opportunity_context"
    )
    @patch(
        "common.tenancy.permissions.IsTenantMember.has_permission",
        return_value=False,
    )
    def test_permission_denied_before_llm(
        self, mock_permission, mock_context, mock_llm
    ):
        response = self.call_view(
            self.make_request(user=self.user)
        )

        self.assertEqual(response.status_code, 403)
        mock_context.assert_not_called()
        mock_llm.assert_not_called()


class AITenantIsolationTests(APITestCase):

    def setUp(self):
        self.user_a = User.objects.create_user(
            email="tenant-a@example.com",
            password="TestPassword123!",
        )

        self.user_b = User.objects.create_user(
            email="tenant-b@example.com",
            password="TestPassword123!",
        )

        
        self.org_a = Organization.objects.create(
            name="Tenant A",
            slug="tenant-a",
            created_by=self.user_a,
        )

        self.org_b = Organization.objects.create(
            name="Tenant B",
            slug="tenant-b",
            created_by=self.user_b,
        )


        Membership.objects.create(
            organization=self.org_a,
            user=self.user_a,
            role=Membership.Role.OWNER,
            is_active=True,
        )

        Membership.objects.create(
            organization=self.org_b,
            user=self.user_b,
            role=Membership.Role.OWNER,
            is_active=True,
        )

        self.client.force_authenticate(user=self.user_a)

    @patch(
        "apps.ai_assistant.views.generate_sales_analysis"
    )
    def test_cannot_analyze_other_tenant_opportunity(
        self,
        mock_llm,
    ):
        from uuid import uuid4

        foreign_opportunity_id = uuid4()

        url = (
            f"/api/v1/organizations/{self.org_b.id}/"
            f"ai/opportunities/{foreign_opportunity_id}/analyze/"
        )

        response = self.client.post(
            url,
            {"question": "Analyze this deal"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        mock_llm.assert_not_called()
        
    
    @patch(
        "apps.ai_assistant.views.generate_sales_analysis"
    )
    def test_foreign_opportunity_never_sent_to_groq(
        self,
        mock_llm,
    ):
        from apps.leads.models import Lead
        from apps.opportunities.models import Opportunity

        # Create a real Lead belonging to Tenant B.
        foreign_lead = Lead.objects.create(
            organization=self.org_b,
            title="Confidential Tenant B Lead",
            created_by=self.user_b,
            status=Lead.Status.QUALIFIED,
        )

        # Convert the test scenario into a real
        # Opportunity record belonging to Tenant B.
        foreign_opportunity = Opportunity.objects.create(
            organization=self.org_b,
            source_lead=foreign_lead,
            title="Confidential Tenant B Opportunity",
            converted_by=self.user_b,
            estimated_value="250000.00",
            currency="PKR",
        )

        # User A requests a Tenant B Opportunity,
        # but supplies Tenant A's organization ID.
        url = (
            f"/api/v1/organizations/{self.org_a.id}/"
            f"ai/opportunities/{foreign_opportunity.id}/analyze/"
        )

        response = self.client.post(
            url,
            {
                "question": (
                    "Analyze this confidential opportunity."
                )
            },
            format="json",
        )

        # The Opportunity must not be visible.
        self.assertEqual(response.status_code, 404)

        # Most importantly, no foreign data
        # should ever be transmitted to Groq.
        mock_llm.assert_not_called()

