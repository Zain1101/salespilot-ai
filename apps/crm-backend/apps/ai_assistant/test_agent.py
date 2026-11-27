
import json
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import PermissionDenied
from django.test import SimpleTestCase

from .agent import AgentError, run_sales_agent


class SalesAgentTests(SimpleTestCase):

    def setUp(self):
        self.user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
        )
        self.organization_id = uuid4()

    def run_agent(self):
        return run_sales_agent(
            user=self.user,
            organization_id=self.organization_id,
            question="Show my overdue tasks.",
        )

    def tool_response(self, name="list_my_tasks",
                      arguments=None):
        return {
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_test_123",
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(
                                arguments
                                if arguments is not None
                                else {"overdue_only": True}
                            ),
                        },
                    },
                ],
            },
        }

    @patch("apps.ai_assistant.agent._request_groq")
    @patch(
        "apps.ai_assistant.agent.authorize_tool_context"
    )
    def test_direct_answer(self, mock_auth, mock_groq):
        mock_groq.return_value = {
            "message": {
                "role": "assistant",
                "content": "Please provide a lead UUID.",
            },
        }

        result = self.run_agent()

        self.assertEqual(
            result["answer"],
            "Please provide a lead UUID.",
        )
        self.assertEqual(result["tools_used"], [])
        self.assertTrue(result["read_only"])
        mock_auth.assert_called_once()
        mock_groq.assert_called_once()

    @patch("apps.ai_assistant.agent._request_groq")
    @patch(
        "apps.ai_assistant.agent.execute_read_only_tool"
    )
    @patch(
        "apps.ai_assistant.agent.authorize_tool_context"
    )
    def test_successful_tool_call(
        self, mock_auth, mock_executor, mock_groq
    ):
        mock_executor.return_value = {
            "tasks": [
                {
                    "title": "Call customer",
                    "is_overdue": True,
                }
            ],
            "returned_count": 1,
        }

        mock_groq.side_effect = [
            self.tool_response(),
            {
                "message": {
                    "role": "assistant",
                    "content": (
                        "You have one overdue task: "
                        "Call customer."
                    ),
                },
            },
        ]

        result = self.run_agent()

        self.assertEqual(
            result["tools_used"],
            ["list_my_tasks"],
        )

        self.assertIn(
            "one overdue task",
            result["answer"],
        )

        self.assertEqual(mock_executor.call_count, 1)
        self.assertEqual(mock_groq.call_count, 2)

        final_messages = (
            mock_groq.call_args.kwargs["messages"]
        )

        tool_message = final_messages[-1]

        self.assertEqual(
            tool_message["role"],
            "tool",
        )
        self.assertEqual(
            tool_message["tool_call_id"],
            "call_test_123",
        )

        self.assertIsNone(
            mock_groq.call_args.kwargs.get("tool_choice")
        )

        self.assertIsNone(
            mock_groq.call_args.kwargs.get("tools")
        )

    @patch("apps.ai_assistant.agent._request_groq")
    @patch(
        "apps.ai_assistant.agent.execute_read_only_tool"
    )
    @patch(
        "apps.ai_assistant.agent.authorize_tool_context"
    )
    def test_unregistered_tool_rejected(
        self, mock_auth, mock_executor, mock_groq
    ):
        mock_groq.return_value = self.tool_response(
            name="delete_all_leads",
            arguments={},
        )

        with self.assertRaises(AgentError):
            self.run_agent()

        mock_executor.assert_not_called()

    @patch("apps.ai_assistant.agent._request_groq")
    @patch(
        "apps.ai_assistant.agent.execute_read_only_tool"
    )
    @patch(
        "apps.ai_assistant.agent.authorize_tool_context"
    )
    def test_too_many_tool_calls_rejected(
        self, mock_auth, mock_executor, mock_groq
    ):
        first = self.tool_response()["message"]["tool_calls"][0]

        mock_groq.return_value = {
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {**first, "id": f"call_{i}"}
                    for i in range(4)
                ],
            },
        }

        with self.assertRaises(AgentError):
            self.run_agent()

        mock_executor.assert_not_called()

    @patch("apps.ai_assistant.agent._request_groq")
    @patch(
        "apps.ai_assistant.agent.authorize_tool_context"
    )
    def test_unauthorized_user_never_calls_groq(
        self, mock_auth, mock_groq
    ):
        mock_auth.side_effect = PermissionDenied(
            "Organization access denied."
        )

        with self.assertRaises(PermissionDenied):
            self.run_agent()

        mock_groq.assert_not_called()

    @patch("apps.ai_assistant.agent._request_groq")
    @patch(
        "apps.ai_assistant.agent.execute_read_only_tool"
    )
    @patch(
        "apps.ai_assistant.agent.authorize_tool_context"
    )
    def test_invalid_final_response_rejected(
        self, mock_auth, mock_executor, mock_groq
    ):
        mock_executor.return_value = {"tasks": []}

        mock_groq.side_effect = [
            self.tool_response(),
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                },
            },
        ]

        with self.assertRaises(AgentError):
            self.run_agent()
