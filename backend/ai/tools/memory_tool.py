"""Memory tool for retrieving working memory context."""

from __future__ import annotations

from backend.ai.tools.base import Tool, ToolPermission


class MemoryTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="memory_lookup",
            description="Read the current working memory context.",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            permission=ToolPermission.READ,
        )

    def execute(self, **kwargs: object) -> str:
        return f"Memory context for query: {kwargs.get('query', '')}"
