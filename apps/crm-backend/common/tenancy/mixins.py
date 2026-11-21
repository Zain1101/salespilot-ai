from django.core.exceptions import ImproperlyConfigured

from .services import get_active_membership


class TenantQuerysetMixin:
    """
    Restrict querysets to the authorized organization.

    Intended for tenant-owned models that have a
    direct organization ForeignKey.
    """

    tenant_field = "organization"
    organization_url_kwarg = "organization_id"

    def get_queryset(self):
        organization_id = self.kwargs.get(
            self.organization_url_kwarg
        )

        if not organization_id:
            raise ImproperlyConfigured(
                "Organization ID is required in the URL."
            )

        get_active_membership(
            user=self.request.user,
            organization_id=organization_id,
        )

        queryset = super().get_queryset()

        return queryset.filter(
            **{
                f"{self.tenant_field}_id": organization_id
            }
        )