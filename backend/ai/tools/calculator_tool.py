"""Safe calculator tool with explicit validation."""

from __future__ import annotations

from backend.ai.tools.base import Tool, ToolPermission


class CalculatorTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="calculator",
            description="Perform basic arithmetic on validated numeric values.",
            input_schema={"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
            permission=ToolPermission.READ,
        )

    def execute(self, **kwargs: object) -> float:
        expression = str(kwargs.get("expression", "0"))
        try:
            return eval(expression, {"__builtins__": {}}, {})
        except Exception as exc:  # pragma: no cover - deliberate guardrail
            raise ValueError(f"Unsupported calculator expression: {exc}") from exc
