"""Routes safe tool calls to the explicit registry."""

from __future__ import annotations

from backend.ai.tools.registry import ToolRegistry


class ToolRouter:
    """Convenience wrapper for tooling requests."""

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or ToolRegistry()

    def route(self, name: str, **kwargs: object) -> object:
        return self.registry.execute(name, **kwargs)
