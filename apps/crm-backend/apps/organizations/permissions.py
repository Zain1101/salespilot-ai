from rest_framework.permissions import BasePermission

from .models import Membership


class IsOrganizationAdmin(BasePermission):
    """
    Only active Owners and Admins of an active
    organization can manage invitations.
    """

    message = "You do not have permission to manage invitations."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        organization = view.get_organization()

        return Membership.objects.filter(
            organization=organization,
            organization__is_active=True,
            user=request.user,
            user__is_active=True,
            is_active=True,
            role__in=[
                Membership.Role.OWNER,
                Membership.Role.ADMIN,
            ],
        ).exists()