from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers

from .models import Organization
from .models import Membership, OrganizationInvitation


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "timezone",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields


class CreateOrganizationSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=255,
        allow_blank=False,
        trim_whitespace=True,
    )

    timezone = serializers.CharField(
        max_length=100,
        default="UTC",
    )

    def validate_timezone(self, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise serializers.ValidationError(
                "Enter a valid IANA timezone."
            )

        return value
    
class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()

    role = serializers.ChoiceField(
        choices=[
            Membership.Role.ADMIN,
            Membership.Role.MANAGER,
            Membership.Role.SALES_REP,
            Membership.Role.VIEWER,
        ]
    )

    def validate_email(self, value):
        return value.strip().lower()


class InvitationSerializer(serializers.ModelSerializer):
    invited_by_email = serializers.EmailField(
        source="invited_by.email",
        read_only=True,
    )

    is_valid = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = OrganizationInvitation

        fields = [
            "id",
            "email",
            "role",
            "status",
            "invited_by_email",
            "expires_at",
            "created_at",
            "accepted_at",
            "is_valid",
        ]

        read_only_fields = fields
        
class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.CharField(
        max_length=256,
        allow_blank=False,
        trim_whitespace=True,
        write_only=True,
    )