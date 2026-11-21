from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import EmailVerificationToken
from .verification_services import (
    request_email_verification,
    verify_email,
)

User = get_user_model()


class EmailVerificationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="verify@example.com",
            password="SecurePassword123!",
        )

    @patch(
        "apps.accounts.verification_services.secrets.token_urlsafe"
    )
    def test_successful_verification(self, mock_token):
        mock_token.return_value = "test-token-123"

        request_email_verification(user=self.user)

        verified_user = verify_email(
            user=self.user,
            token="test-token-123",
        )

        self.assertTrue(verified_user.email_verified)

        record = EmailVerificationToken.objects.get(
            user=self.user
        )

        self.assertIsNotNone(record.consumed_at)

    @patch(
        "apps.accounts.verification_services.secrets.token_urlsafe"
    )
    def test_invalid_token_rejected(self, mock_token):
        from django.core.exceptions import ValidationError

        mock_token.return_value = "correct-token"

        request_email_verification(user=self.user)

        with self.assertRaises(ValidationError):
            verify_email(
                user=self.user,
                token="incorrect-token",
            )

    @patch(
        "apps.accounts.verification_services.secrets.token_urlsafe"
    )
    def test_token_cannot_be_reused(self, mock_token):
        from django.core.exceptions import ValidationError

        mock_token.return_value = "single-use-token"

        request_email_verification(user=self.user)

        verify_email(
            user=self.user,
            token="single-use-token",
        )

        with self.assertRaises(ValidationError):
            verify_email(
                user=self.user,
                token="single-use-token",
            )

    @patch(
        "apps.accounts.verification_services.secrets.token_urlsafe"
    )
    def test_other_user_cannot_verify(self, mock_token):
        from django.core.exceptions import ValidationError

        mock_token.return_value = "private-token"

        request_email_verification(user=self.user)

        other_user = User.objects.create_user(
            email="other@example.com",
            password="AnotherSecurePassword123!",
        )

        with self.assertRaises(ValidationError):
            verify_email(
                user=other_user,
                token="private-token",
            )