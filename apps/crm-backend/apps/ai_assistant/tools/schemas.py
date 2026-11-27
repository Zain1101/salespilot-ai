
"""
Public tool schemas exposed to Groq.

These schemas describe permitted arguments.
They never include organization_id or user_id.

Actual authorization happens in Django.
"""


def get_groq_tool_schemas():
    return [
        {
            "type": "function",
            "function": {
                "name": "get_opportunity",
                "description": (
                    "Retrieve details of one CRM opportunity "
                    "using its UUID. Returns the status, "
                    "value, pipeline and stage."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "opportunity_id": {
                            "type": "string",
                            "description": (
                                "UUID of the CRM opportunity"
                            ),
                        },
                    },
                    "required": ["opportunity_id"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_lead",
                "description": (
                    "Retrieve one CRM lead by UUID, "
                    "including status, assignment and "
                    "conversion information."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_id": {
                            "type": "string",
                            "description": "UUID of the CRM lead",
                        },
                    },
                    "required": ["lead_id"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_my_tasks",
                "description": (
                    "List pending sales tasks assigned to "
                    "the authenticated user. Can return "
                    "only overdue tasks if requested."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "overdue_only": {
                            "type": "boolean",
                            "description": (
                                "True to return overdue tasks only"
                            ),
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 20,
                        },
                    },
                    "additionalProperties": False,
                },
            },
        },
    ]
