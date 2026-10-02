"""Explicitly registered tool registry."""

from __future__ import annotations

from backend.ai.tools.base import Tool, ToolPermission


class ToolRegistry:
    """Container for tools that are allowed to be invoked by the assistant."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def execute(self, name: str, **kwargs: object) -> object:
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")
        if tool.permission == ToolPermission.RESTRICTED and kwargs.get("confirm") is not True:
            raise PermissionError(f"Tool {name} requires explicit confirmation.")
        return tool.execute(**kwargs)
