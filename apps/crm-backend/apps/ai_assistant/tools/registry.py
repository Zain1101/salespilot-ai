
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ReadOnlyTool:
    name: str
    description: str
    handler: Callable


class ToolRegistry:
    """
    Registry of explicitly approved CRM tools.

    Tools must enforce tenant authorization themselves.
    """

    def __init__(self):
        self._tools = {}

    def register(self, tool: ReadOnlyTool):
        if not tool.name or not callable(tool.handler):
            raise ValueError("Invalid tool registration.")

        if tool.name in self._tools:
            raise ValueError(
                f"Tool already registered: {tool.name}"
            )

        self._tools[tool.name] = tool

    def get(self, name: str) -> ReadOnlyTool:
        try:
            return self._tools[name]
        except KeyError:
            raise ValueError("Unknown AI tool.") from None

    def list_tools(self):
        return [
            {
                "name": tool.name,
                "description": tool.description,
            }
            for tool in self._tools.values()
        ]


registry = ToolRegistry()
