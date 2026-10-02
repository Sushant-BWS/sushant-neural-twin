"""Preference metadata that is explicitly documented only."""

from __future__ import annotations


class Preferences:
    """Stores known preference facts for later use in responses."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def add(self, key: str, value: str) -> None:
        self.values[key] = value
