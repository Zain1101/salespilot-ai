from rest_framework import serializers


class SalesOverviewQuerySerializer(serializers.Serializer):

    currency = serializers.ChoiceField(
        choices=[
            ("PKR", "PKR"),
            ("USD", "USD"),
            ("EUR", "EUR"),
        ],
        required=True,
    )