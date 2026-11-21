from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from django.conf import settings

from .managers import UserManager


class User(AbstractUser):
    username = None
    
    email = models.EmailField(
        unique=True,
        max_length=254,
    )
    email_verified = models.BooleanField(default=False)
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
    
class EmailVerificationToken(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
    )

    token_hash = models.CharField(
        max_length=64,
        unique=True,
    )

    expires_at = models.DateTimeField()

    consumed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Email verification for user {self.user_id}"