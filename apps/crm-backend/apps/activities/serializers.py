from rest_framework import serializers

from .models import Activity


class ActivityCreateSerializer(serializers.Serializer):

    activity_type = serializers.ChoiceField(
        choices=Activity.Type.choices,
    )

    subject = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=10000,
    )

    occurred_at = serializers.DateTimeField(
        required=False,
    )

    lead_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    company_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    contact_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    opportunity_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        target_fields = [
            "lead_id",
            "company_id",
            "contact_id",
            "opportunity_id",
        ]

        supplied = [
            field for field in target_fields
            if attrs.get(field) is not None
        ]

        if len(supplied) != 1:
            raise serializers.ValidationError(
                "Provide exactly one linked CRM entity."
            )

        return attrs


class ActivitySerializer(serializers.ModelSerializer):

    created_by_email = serializers.EmailField(
        source="created_by.email",
        read_only=True,
    )

    entity_type = serializers.SerializerMethodField()
    entity_id = serializers.SerializerMethodField()

    class Meta:
        model = Activity

        fields = [
            "id",
            "organization",
            "activity_type",
            "subject",
            "description",
            "created_by",
            "created_by_email",
            "occurred_at",
            "created_at",
            "lead",
            "company",
            "contact",
            "opportunity",
            "entity_type",
            "entity_id",
        ]

        read_only_fields = fields

    def get_entity_type(self, obj):
        for field in (
            "lead", "company", "contact", "opportunity"
        ):
            if getattr(obj, f"{field}_id") is not None:
                return field
        return None

    def get_entity_id(self, obj):
        entity_type = self.get_entity_type(obj)

        if entity_type is None:
            return None

        return str(
            getattr(obj, f"{entity_type}_id")
        )