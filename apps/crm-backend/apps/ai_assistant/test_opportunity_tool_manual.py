
from django.contrib.auth import get_user_model

from apps.ai_assistant.tools.executor import (
    authorize_tool_context,
    execute_read_only_tool,
)


ORG_ID = "0b2286a7-98a5-4425-9cf1-695d952b8f4b"

OPPORTUNITY_ID = "51937afb-15ca-4aaf-9798-ce7205205226"


def main():
    User = get_user_model()

    user = User.objects.get(
        email="syed1zain2080@gmail.com"
    )

    context = authorize_tool_context(
        user=user,
        organization_id=ORG_ID,
    )

    result = execute_read_only_tool(
        tool_name="get_opportunity",
        arguments={
            "opportunity_id": OPPORTUNITY_ID,
        },
        context=context,
    )

    print("\nOpportunity tool result:\n")

    import json

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
