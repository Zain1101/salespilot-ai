from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Notification

        fields = [
            "id",
            "organization",
            "recipient",
            "task",
            "notification_type",
            "title",
            "message",
            "is_read",
            "read_at",
            "created_at",
            "resolved_at",
        ]

        read_only_fields = fields