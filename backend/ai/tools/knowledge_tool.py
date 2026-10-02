"""Knowledge lookup tool."""

from __future__ import annotations

from backend.ai.tools.base import Tool, ToolPermission


class KnowledgeTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="knowledge_lookup",
            description="Look up documented facts from the local knowledge base.",
            input_schema={"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]},
            permission=ToolPermission.READ,
        )

    def execute(self, **kwargs: object) -> str:
        question = str(kwargs.get("question", ""))
        return f"Knowledge lookup for: {question}"
