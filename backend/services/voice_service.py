"""Voice orchestration service."""

from __future__ import annotations


class VoiceService:
    def render_status(self, available: bool = True) -> dict[str, object]:
        return {"available": available, "provider": "local"}
