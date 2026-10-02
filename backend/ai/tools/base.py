"""Safe tool interface and permission model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolPermission(str, Enum):
    READ = "read"
    WRITE = "write"
    RESTRICTED = "restricted"


@dataclass(slots=True)
class Tool:
    """A safe, explicitly-registered callable tool."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    permission: ToolPermission = ToolPermission.READ

    def execute(self, **kwargs: Any) -> Any:
        raise NotImplementedError
