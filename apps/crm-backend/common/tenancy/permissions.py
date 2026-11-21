from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from .services import (
    get_active_membership,
    require_organization_role,
)

from apps.organizations.models import Membership


class IsTenantMember(BasePermission):
    message = "You cannot access this organization."

    def has_permission(self, request, view):
        organization_id = view.kwargs.get("organization_id")

        if not organization_id:
            return False

        try:
            get_active_membership(
                user=request.user,
                organization_id=organization_id,
            )
            return True

        except PermissionDenied:
            return False


class IsTenantAdmin(BasePermission):
    message = "Organization administrator access required."

    def has_permission(self, request, view):
        organization_id = view.kwargs.get("organization_id")

        if not organization_id:
            return False

        try:
            require_organization_role(
                user=request.user,
                organization_id=organization_id,
                allowed_roles=[
                    Membership.Role.OWNER,
                    Membership.Role.ADMIN,
                ],
            )
            return True

        except PermissionDenied:
            return False