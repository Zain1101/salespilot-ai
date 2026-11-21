from rest_framework import serializers

from .models import Pipeline, PipelineStage


class PipelineStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PipelineStage

        fields = [
            "id",
            "name",
            "position",
            "probability",
        ]

        read_only_fields = fields


class PipelineSerializer(serializers.ModelSerializer):
    stages = PipelineStageSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Pipeline

        fields = [
            "id",
            "name",
            "is_default",
            "is_active",
            "stages",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class PipelineCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=150,
        trim_whitespace=True,
    )