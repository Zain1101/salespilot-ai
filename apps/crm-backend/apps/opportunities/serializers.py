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
    pipeline_name = serializers.CharField(
        source="pipeline.name",
        read_only=True,
        default=None,
    )

    stage_name = serializers.CharField(
        source="stage.name",
        read_only=True,
        default=None,
    )

    stage_probability = serializers.IntegerField(
        source="stage.probability",
        read_only=True,
        default=None,
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
            "pipeline",
            "pipeline_name",
            "stage",
            "stage_name",
            "stage_probability",
            "actual_value",
            "closed_at",
            "closed_by",
            "loss_reason",
        ]

        read_only_fields = fields

    def get_contact_name(self, obj):
        return str(obj.contact) if obj.contact else None

class OpportunityStageTransitionSerializer(
    serializers.Serializer
):
    stage_id = serializers.UUIDField()

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        trim_whitespace=True,
    )
    
class OpportunityCloseSerializer(serializers.Serializer):

    outcome = serializers.ChoiceField(
        choices=[
            ("won", "Won"),
            ("lost", "Lost"),
        ]
    )

    actual_value = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )

    loss_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        trim_whitespace=True,
    )

    def validate(self, attrs):
        outcome = attrs["outcome"]

        if outcome == "won":
            if attrs.get("actual_value") is None:
                raise serializers.ValidationError({
                    "actual_value": (
                        "Actual value is required for Won deals."
                    )
                })

            if attrs.get("loss_reason"):
                raise serializers.ValidationError({
                    "loss_reason": (
                        "Loss reason is only used for Lost deals."
                    )
                })

        if outcome == "lost":
            if not attrs.get("loss_reason", "").strip():
                raise serializers.ValidationError({
                    "loss_reason": (
                        "A loss reason is required."
                    )
                })

            if attrs.get("actual_value") is not None:
                raise serializers.ValidationError({
                    "actual_value": (
                        "Actual value is only used for Won deals."
                    )
                })

        return attrs