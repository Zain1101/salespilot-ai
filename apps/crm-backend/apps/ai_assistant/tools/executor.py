
import json
from dataclasses import dataclass

from django.core.exceptions import PermissionDenied

from apps.organizations.models import (
    Organization,
    Membership,
)

from .registry import registry


MAX_ARGUMENT_BYTES = 4096
MAX_RESULT_BYTES = 16000


@dataclass(frozen=True)
class ToolExecutionContext:
    """
    Trusted context created by the backend.

    Never construct this from LLM-supplied arguments.
    """

    organization: Organization
    membership: Membership
    user: object


class ToolExecutionError(Exception):
    pass


def authorize_tool_context(*, user, organization_id):
    """
    Validate the user and active organization membership.
    """

    if (
        user is None
        or not getattr(user, "is_authenticated", False)
        or not getattr(user, "is_active", False)
    ):
        raise PermissionDenied("Authentication required.")

    organization = Organization.objects.filter(
        pk=organization_id,
        is_active=True,
    ).first()

    if organization is None:
        raise PermissionDenied(
            "Organization access denied."
        )

    membership = Membership.objects.filter(
        organization=organization,
        user=user,
        is_active=True,
    ).first()

    if membership is None:
        raise PermissionDenied(
            "Organization access denied."
        )

    return ToolExecutionContext(
        organization=organization,
        membership=membership,
        user=user,
    )


def execute_read_only_tool(
    *,
    tool_name,
    arguments,
    context,
):
    """
    Execute a registered read-only tool.

    The context must come from authorize_tool_context().
    """

    if not isinstance(context, ToolExecutionContext):
        raise ToolExecutionError(
            "Invalid tool execution context."
        )

    if not isinstance(tool_name, str):
        raise ToolExecutionError("Invalid tool name.")

    if not isinstance(arguments, dict):
        raise ToolExecutionError(
            "Tool arguments must be an object."
        )

    try:
        arguments_json = json.dumps(arguments)
    except (TypeError, ValueError) as exc:
        raise ToolExecutionError(
            "Invalid tool arguments."
        ) from exc

    if len(arguments_json.encode("utf-8")) > MAX_ARGUMENT_BYTES:
        raise ToolExecutionError(
            "Tool arguments exceed the size limit."
        )

    # Never allow the LLM to choose its tenant.
    if "organization_id" in arguments or "user_id" in arguments:
        raise ToolExecutionError(
            "Reserved arguments are not allowed."
        )

    try:
        tool = registry.get(tool_name)
    except ValueError as exc:
        raise ToolExecutionError(
            "Unknown or unavailable tool."
        ) from exc

    # Handlers receive trusted authorization context.
    result = tool.handler(
        context=context,
        arguments=arguments,
    )

    try:
        serialized = json.dumps(result, default=str)
    except (TypeError, ValueError) as exc:
        raise ToolExecutionError(
            "Tool returned an invalid result."
        ) from exc

    if len(serialized.encode("utf-8")) > MAX_RESULT_BYTES:
        raise ToolExecutionError(
            "Tool result exceeds the size limit."
        )

    return result
