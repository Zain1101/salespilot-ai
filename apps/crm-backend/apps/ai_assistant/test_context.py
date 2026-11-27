
import json
import os

import django


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

django.setup()


from django.contrib.auth import get_user_model
from apps.ai_assistant.context import build_opportunity_context


User = get_user_model()


def main():

    organization_id = (
        "0b2286a7-98a5-4425-9cf1-695d952b8f4b"
    )

    opportunity_id = (
        "51937afb-15ca-4aaf-9798-ce7205205226"
    )

    user = User.objects.get(
        email="syed1zain2080@gmail.com"
    )

    context = build_opportunity_context(
        organization_id=organization_id,
        opportunity_id=opportunity_id,
        requested_by=user,
    )

    print("\nCRM context retrieved successfully!\n")

    print(
        json.dumps(
            context,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()

