from urllib.parse import urlsplit

from rest_framework import serializers

from .models import Company


class CompanySerializer(serializers.ModelSerializer):

    class Meta:
        model = Company

        fields = [
            "id",
            "name",
            "industry",
            "website",
            "domain",
            "phone",
            "email",
            "size",
            "country",
            "city",
            "address",
            "description",
            "is_archived",
            "created_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "domain",
            "is_archived",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Company name is required."
            )

        return value

    def validate(self, attrs):
        website = attrs.get(
            "website",
            self.instance.website if self.instance else "",
        )

        if website:
            hostname = urlsplit(website).hostname

            if not hostname:
                raise serializers.ValidationError({
                    "website": "Invalid website hostname."
                })

            attrs["domain"] = hostname.lower().rstrip(".")
        else:
            attrs["domain"] = ""

        return attrs