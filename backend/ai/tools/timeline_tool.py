"""Timeline-related tool for retrieving timeline events."""

from __future__ import annotations

from backend.ai.tools.base import Tool, ToolPermission


class TimelineTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="timeline_lookup",
            description="Retrieve a chronological summary of personal milestones and career events.",
            input_schema={"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"]},
            permission=ToolPermission.READ,
        )

    def execute(self, **kwargs: object) -> str:
        topic = str(kwargs.get("topic", "general"))
        return f"Timeline summary for {topic}"
