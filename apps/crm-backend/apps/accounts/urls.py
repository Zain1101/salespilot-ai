from django.urls import path

from .views import RegisterView, CurrentUserView
from .views import (
    RequestEmailVerificationView,
    ConfirmEmailVerificationView,
)

urlpatterns = [
    path(
        "register/",
        RegisterView.as_view(),
        name="register",
    ),
    
    path(
        "me/",
        CurrentUserView.as_view(),
        name="current-user",
    ),
    
    path(
    "verify-email/request/",
    RequestEmailVerificationView.as_view(),
    name="request-email-verification",
    ),

    path(
        "verify-email/confirm/",
        ConfirmEmailVerificationView.as_view(),
        name="confirm-email-verification",
    ),
]