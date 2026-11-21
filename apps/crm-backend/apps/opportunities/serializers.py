from rest_framework import serializers

from .models import Opportunity


class OpportunitySerializer(serializers.ModelSerializer):

    source_lead = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )

    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
        default=None,
    )

    contact_name = serializers.SerializerMethodField()

    converted_by_email = serializers.EmailField(
        source="converted_by.email",
        read_only=True,
    )

    class Meta:
        model = Opportunity

        fields = [
            "id",
            "organization",
            "source_lead",
            "company",
            "company_name",
            "contact",
            "contact_name",
            "title",
            "estimated_value",
            "currency",
            "status",
            "converted_by",
            "converted_by_email",
            "converted_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields

    def get_contact_name(self, obj):
        return str(obj.contact) if obj.contact else None