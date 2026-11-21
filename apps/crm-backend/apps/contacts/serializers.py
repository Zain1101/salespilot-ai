from rest_framework import serializers

from apps.companies.models import Company
from .models import Contact


class ContactSerializer(serializers.ModelSerializer):

    company = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.none(),
        required=False,
        allow_null=True,
    )

    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
        default=None,
    )

    class Meta:
        model = Contact

        fields = [
            "id",
            "company",
            "company_name",
            "first_name",
            "last_name",
            "email",
            "phone",
            "job_title",
            "department",
            "linkedin_url",
            "city",
            "country",
            "notes",
            "is_primary",
            "is_archived",
            "created_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "company_name",
            "is_archived",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        view = self.context.get("view")

        if request is None or view is None:
            return

        organization_id = view.kwargs.get(
            "organization_id"
        )

        if organization_id is None:
            return

        # A submitted company UUID must belong
        # to the same SalesPilot organization.
        self.fields["company"].queryset = (
            Company.objects.filter(
                organization_id=organization_id,
                is_archived=False,
            )
        )

    def validate_first_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "First name is required."
            )

        return value

    def validate_email(self, value):
        return value.strip().lower()