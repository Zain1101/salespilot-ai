from django.contrib import admin

from .models import Organization, Membership
from .models import OrganizationInvitation


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "is_active",
        "created_at",
    )

    search_fields = ("name", "slug")

    readonly_fields = ("created_at", "updated_at")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "organization",
        "role",
        "is_active",
    )

    list_filter = ("role", "is_active")
    
@admin.register(OrganizationInvitation)
class OrganizationInvitationAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "organization",
        "role",
        "status",
        "expires_at",
        "created_at",
    )

    list_filter = (
        "status",
        "role",
    )

    search_fields = (
        "email",
        "organization__name",
    )

    readonly_fields = (
        "token_hash",
        "created_at",
        "accepted_at",
    )