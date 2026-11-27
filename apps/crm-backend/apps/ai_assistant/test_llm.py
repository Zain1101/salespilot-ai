import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

from .llm import AIProviderError, generate_sales_analysis


class LLMServiceTests(TestCase):

    @patch.dict(os.environ, {"GROQ_API_KEY": ""})
    def test_missing_api_key(self):
        with self.assertRaises(AIProviderError):
            generate_sales_analysis(
                question="Analyze this opportunity",
                context={},
            )

    @patch.dict(
        os.environ,
        {
            "GROQ_API_KEY": "test-key",
            "GROQ_MODEL": "openai/gpt-oss-20b",
        },
    )
    @patch("apps.ai_assistant.llm.httpx.Client")
    def test_successful_analysis(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "model": "openai/gpt-oss-20b",
            "choices": [
                {
                    "message": {
                        "content": "The deal is already Won."
                    }
                }
            ],
        }

        mock_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        result = generate_sales_analysis(
            question="What should we do next?",
            context={
                "opportunity": {"status": "won"},
            },
        )

        self.assertEqual(
            result["answer"],
            "The deal is already Won.",
        )

        payload = (
            mock_client.return_value
            .__enter__.return_value.post
            .call_args.kwargs["json"]
        )

        self.assertIn(
            '"status": "won"',
            payload["messages"][1]["content"],
        )

        self.assertEqual(len(payload["messages"]), 2)

    @patch.dict(
        os.environ,
        {"GROQ_API_KEY": "test-key"},
    )
    @patch("apps.ai_assistant.llm.httpx.Client")
    def test_empty_model_response(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": ""}}
            ],
        }

        mock_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        with self.assertRaises(AIProviderError):
            generate_sales_analysis(
                question="Analyze",
                context={},
            )