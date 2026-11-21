from rest_framework import serializers

from .models import SalesTask


class SalesTaskCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)

    description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=10000,
    )

    assigned_to_id = serializers.UUIDField()

    due_at = serializers.DateTimeField()

    priority = serializers.ChoiceField(
        choices=SalesTask.Priority.choices,
        default=SalesTask.Priority.MEDIUM,
    )

    lead_id = serializers.UUIDField(required=False)
    company_id = serializers.UUIDField(required=False)
    contact_id = serializers.UUIDField(required=False)
    opportunity_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        targets = [
            "lead_id",
            "company_id",
            "contact_id",
            "opportunity_id",
        ]

        if sum(attrs.get(key) is not None for key in targets) != 1:
            raise serializers.ValidationError(
                "Exactly one linked CRM entity is required."
            )

        return attrs


class SalesTaskSerializer(serializers.ModelSerializer):
    assigned_to_email = serializers.EmailField(
        source="assigned_to.user.email",
        read_only=True,
    )

    created_by_email = serializers.EmailField(
        source="created_by.email",
        read_only=True,
    )

    class Meta:
        model = SalesTask
        fields = [
            "id",
            "organization",
            "title",
            "description",
            "priority",
            "status",
            "assigned_to",
            "assigned_to_email",
            "due_at",
            "lead",
            "company",
            "contact",
            "opportunity",
            "created_by",
            "created_by_email",
            "completed_by",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TaskStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ]
    )

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
    )