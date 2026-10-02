"""Adapt structured personal thought records into the Thought schema."""

from typing import Any

from backend.knowledge.schemas import Thought


class ThoughtAdapter:
    """Convert raw personal thought records into documented Thought objects."""

    @staticmethod
    def adapt(record: dict[str, Any]) -> Thought:
        """Convert one raw thought record into a Thought model."""

        topic = str(record.get("topic", "")).strip()
        statement = str(record.get("statement", "")).strip()
        source = str(record.get("source", "")).strip()

        if not topic:
            raise ValueError("Thought record is missing 'topic'.")

        if not statement:
            raise ValueError("Thought record is missing 'statement'.")

        if not source:
            raise ValueError("Thought record is missing 'source'.")

        # Preserve additional thought context instead of throwing it away.
        context_fields = {
            "id": record.get("id"),
            "title": record.get("title"),
            "mindset": record.get("mindset"),
            "daily_behavior": record.get("daily_behavior"),
            "core_belief": record.get("core_belief"),
            "strength": record.get("strength"),
        }

        context_fields = {
            key: value
            for key, value in context_fields.items()
            if value is not None
        }

        context = str(context_fields)

        evidence = []

        if record.get("evidence"):
            raw_evidence = record["evidence"]

            if isinstance(raw_evidence, list):
                evidence = [
                    str(item).strip()
                    for item in raw_evidence
                    if str(item).strip()
                ]
            else:
                evidence = [str(raw_evidence).strip()]

        return Thought(
            id=str(record.get("id", "")),
            source=source,
            confidence=float(record.get("confidence", 0.0)),
            topic=topic,
            statement=statement,
            context=context,
            evidence=evidence,
        )