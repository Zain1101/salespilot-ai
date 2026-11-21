from django.core.exceptions import PermissionDenied

from apps.organizations.models import (
    Organization,
    Membership,
)


def get_active_membership(*, user, organization_id):
    """
    Return active membership for the requested
    organization, otherwise deny access.
    """

    if (
        not user
        or not user.is_authenticated
        or not user.is_active
    ):
        raise PermissionDenied("Authentication required.")

    membership = (
        Membership.objects
        .select_related("organization")
        .filter(
            user=user,
            organization_id=organization_id,
            is_active=True,
            organization__is_active=True,
        )
        .first()
    )

    if membership is None:
        raise PermissionDenied(
            "You do not have access to this organization."
        )

    return membership


def require_organization_role(
    *,
    user,
    organization_id,
    allowed_roles,
):
    """
    Ensure the user has an allowed role
    in the requested organization.
    """

    membership = get_active_membership(
        user=user,
        organization_id=organization_id,
    )

    if membership.role not in allowed_roles:
        raise PermissionDenied(
            "Insufficient organization permissions."
        )

    return membership