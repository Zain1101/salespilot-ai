from rest_framework import serializers

from apps.companies.models import Company
from apps.contacts.models import Contact
from apps.organizations.models import Membership

from .models import Lead


ASSIGNABLE_ROLES = [
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.MANAGER,
    Membership.Role.SALES_REP,
]


class LeadSerializer(serializers.ModelSerializer):

    company = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.none(),
        required=False,
        allow_null=True,
    )

    contact = serializers.PrimaryKeyRelatedField(
        queryset=Contact.objects.none(),
        required=False,
        allow_null=True,
    )

    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=Membership.objects.none(),
        required=False,
        allow_null=True,
    )

    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
        default=None,
    )

    contact_name = serializers.SerializerMethodField()

    assigned_to_email = serializers.EmailField(
        source="assigned_to.user.email",
        read_only=True,
        default=None,
    )

    class Meta:
        model = Lead

        fields = [
            "id",
            "title",
            "company",
            "company_name",
            "contact",
            "contact_name",
            "assigned_to",
            "assigned_to_email",
            "source",
            "status",
            "priority",
            "estimated_value",
            "currency",
            "description",
            "is_archived",
            "created_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "company_name",
            "contact_name",
            "assigned_to_email",
            "status",
            "is_archived",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        view = self.context.get("view")

        if view is None:
            return

        organization_id = view.kwargs.get(
            "organization_id"
        )

        if organization_id is None:
            return

        self.fields["company"].queryset = (
            Company.objects.filter(
                organization_id=organization_id,
                is_archived=False,
            )
        )

        self.fields["contact"].queryset = (
            Contact.objects.filter(
                organization_id=organization_id,
                is_archived=False,
            )
        )

        self.fields["assigned_to"].queryset = (
            Membership.objects.filter(
                organization_id=organization_id,
                is_active=True,
                user__is_active=True,
                role__in=ASSIGNABLE_ROLES,
            )
        )

    def get_contact_name(self, obj):
        if obj.contact is None:
            return None

        return str(obj.contact)

    def validate_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Lead title is required."
            )

        return value

    def validate(self, attrs):

        company = attrs.get(
            "company",
            self.instance.company if self.instance else None,
        )

        contact = attrs.get(
            "contact",
            self.instance.contact if self.instance else None,
        )

        assigned_to = attrs.get(
            "assigned_to",
            self.instance.assigned_to
            if self.instance else None,
        )

        organization_id = (
            self.context["view"].kwargs["organization_id"]
        )

        if company is not None and (
            company.organization_id != organization_id
            or company.is_archived
        ):
            raise serializers.ValidationError({
                "company": "Company is not available."
            })

        if contact is not None:

            if (
                contact.organization_id != organization_id
                or contact.is_archived
            ):
                raise serializers.ValidationError({
                    "contact": "Contact is not available."
                })

            if contact.company_id is not None:
                if company is None or contact.company_id != company.pk:
                    raise serializers.ValidationError({
                        "contact": (
                            "Contact must belong to "
                            "the selected company."
                        )
                    })

        if assigned_to is not None:

            if (
                assigned_to.organization_id != organization_id
                or not assigned_to.is_active
                or not assigned_to.user.is_active
                or assigned_to.role not in ASSIGNABLE_ROLES
            ):
                raise serializers.ValidationError({
                    "assigned_to": (
                        "Assigned employee is not available."
                    )
                })

        return attrs