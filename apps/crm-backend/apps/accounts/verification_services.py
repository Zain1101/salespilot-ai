import hashlib
import secrets

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import EmailVerificationToken, User


def hash_token(token):
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


@transaction.atomic
def request_email_verification(*, user):
    if not user.is_active:
        raise ValidationError("User account is inactive.")

    if user.email_verified:
        raise ValidationError("Email is already verified.")

    # Invalidate old verification tokens for this user.
    EmailVerificationToken.objects.filter(
        user=user,
        consumed_at__isnull=True,
    ).delete()

    raw_token = secrets.token_urlsafe(32)

    verification = EmailVerificationToken.objects.create(
        user=user,
        token_hash=hash_token(raw_token),
        expires_at=timezone.now() + timedelta(hours=24),
    )

    # Development link. Next.js page will be built later.
    verification_link = (
        "http://localhost:3000/verify-email"
        f"?token={raw_token}"
    )

    def send_verification_email():
        send_mail(
            subject="Verify your SalesPilot AI email",
            message=(
                "Welcome to SalesPilot AI!\n\n"
                "Verify your email using this link:\n"
                f"{verification_link}\n\n"
                "This link expires in 24 hours."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

    transaction.on_commit(send_verification_email)

    return verification


@transaction.atomic
def verify_email(*, user, token):
    if user.email_verified:
        raise ValidationError("Email is already verified.")

    if not token or not isinstance(token, str):
        raise ValidationError("Invalid verification token.")

    verification = (
        EmailVerificationToken.objects
        .select_for_update()
        .filter(
            token_hash=hash_token(token),
            user=user,
        )
        .first()
    )

    if verification is None:
        raise ValidationError("Invalid verification token.")

    if verification.consumed_at is not None:
        raise ValidationError("Token has already been used.")

    if timezone.now() >= verification.expires_at:
        raise ValidationError("Verification token has expired.")

    # Lock the user record and recheck current state.
    locked_user = User.objects.select_for_update().get(pk=user.pk)

    if not locked_user.is_active:
        raise ValidationError("User account is inactive.")

    if locked_user.email_verified:
        raise ValidationError("Email is already verified.")

    locked_user.email_verified = True
    locked_user.save(update_fields=["email_verified"])

    verification.consumed_at = timezone.now()
    verification.save(update_fields=["consumed_at"])

    # Invalidate any other outstanding verification tokens.
    EmailVerificationToken.objects.filter(
        user=locked_user,
        consumed_at__isnull=True,
    ).exclude(pk=verification.pk).delete()

    return locked_user