
from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from common.tenancy.permissions import IsTenantMember
from .context import build_opportunity_context
from .llm import AIProviderError, generate_sales_analysis
from .serializers import OpportunityAIRequestSerializer
import logging
from rest_framework.throttling import ScopedRateThrottle
from .agent import run_sales_agent, AgentError
from .serializers import SalesAgentRequestSerializer

logger = logging.getLogger(__name__)

class OpportunityAIAnalysisView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]

    def post(self, request, organization_id, pk):

        serializer = OpportunityAIRequestSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        # Retrieve CRM context only after authentication
        # and tenant authorization.
        try:
            context = build_opportunity_context(
                organization_id=organization_id,
                opportunity_id=pk,
                requested_by=request.user,
            )

        except PermissionDenied:
            return Response(
                {"detail": "Access denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Http404 from the context service is handled
        # automatically by Django REST Framework.

        question = serializer.validated_data["question"]

        try:
            analysis = generate_sales_analysis(
                question=question,
                context=context,
            )

        except AIProviderError:
            logger.exception(
                "Groq AI analysis failed for opportunity %s",
                pk,
            )
            return Response(
                {
                    "detail": (
                        "AI analysis is temporarily unavailable."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "opportunity_id": context[
                    "opportunity"
                ]["id"],
                "question": question,
                "answer": analysis["answer"],
                "model": analysis["model"],
                "context_event_count": len(
                    context["recent_events"]
                ),
                "timeline_has_more": context[
                    "timeline_has_more"
                ],
                "read_only": True,
            },
            status=status.HTTP_200_OK,
        )

class SalesAgentView(APIView):
    """
    JWT-protected, organization-scoped AI agent.

    Read-only: the agent cannot modify CRM records.
    """

    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai_agent"

    def post(self, request, organization_id):

        serializer = SalesAgentRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        question = serializer.validated_data["question"]

        try:
            result = run_sales_agent(
                user=request.user,
                organization_id=organization_id,
                question=question,
            )

        except AgentError:
            logging.getLogger(__name__).warning(
                "AI agent request failed for organization %s",
                organization_id,
            )

            return Response(
                {
                    "detail": (
                        "AI agent is temporarily unavailable."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "answer": result["answer"],
                "tools_used": result["tools_used"],
                "read_only": True,
            },
            status=status.HTTP_200_OK,
        )
