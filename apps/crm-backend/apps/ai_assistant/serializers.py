
from rest_framework import serializers


class OpportunityAIRequestSerializer(serializers.Serializer):

    question = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=1000,
        trim_whitespace=True,
        default=(
            "Analyze this opportunity, identify "
            "potential sales risks, and recommend "
            "the next appropriate actions."
        ),
    )
