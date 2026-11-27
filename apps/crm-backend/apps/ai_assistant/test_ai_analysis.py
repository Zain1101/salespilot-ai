
import os
import sys

import django


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

django.setup()


from django.contrib.auth import get_user_model

from apps.ai_assistant.context import (
    build_opportunity_context,
)
from apps.ai_assistant.llm import (
    AIProviderError,
    generate_sales_analysis,
)


ORG_ID = "0b2286a7-98a5-4425-9cf1-695d952b8f4b"
OPPORTUNITY_ID = "51937afb-15ca-4aaf-9798-ce7205205226"


def main():
    if not os.getenv("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY is not configured.")
        sys.exit(1)

    User = get_user_model()

    # Local development script only.
    # Use the known development owner account.
    user = User.objects.get(pk=1)

    context = build_opportunity_context(
        organization_id=ORG_ID,
        opportunity_id=OPPORTUNITY_ID,
        requested_by=user,
    )

    print("CRM context retrieved successfully.")
    print("Opportunity:", context["opportunity"]["title"])
    print("Status:", context["opportunity"]["status"])
    print("Timeline events:", len(context["recent_events"]))

    question = (
        "Analyze this sales opportunity. "
        "Summarize the current situation, "
        "identify risks or missing information, "
        "and recommend the next appropriate actions."
    )

    try:
        result = generate_sales_analysis(
            question=question,
            context=context,
        )

    except AIProviderError:
        print("AI analysis failed. Check your Groq configuration.")
        sys.exit(1)

    print("\nMODEL:", result["model"])
    print("\nSALES ANALYSIS\n")
    print(result["answer"])


if __name__ == "__main__":
    main()
