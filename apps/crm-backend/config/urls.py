from django.contrib import admin
from django.urls import path, include

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from apps.organizations.invitation_views import AcceptInvitationView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/v1/health/", include("health.urls")),

    path(
        "api/v1/auth/login/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),

    path(
        "api/v1/auth/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

    path(
        "api/v1/auth/",
        include("apps.accounts.urls"),
    ),
    
    path(
    "api/v1/organizations/",
    include("apps.organizations.urls"),
    ),
    
    path(
    "api/v1/invitations/accept/",
    AcceptInvitationView.as_view(),
    name="accept-invitation",
    ),
]