from rest_framework import serializers


class OpportunityTimelineQuerySerializer(
    serializers.Serializer
):
    limit = serializers.IntegerField(
        required=False,
        default=20,
        min_value=1,
        max_value=100,
    )