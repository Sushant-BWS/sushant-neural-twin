"""Load documented personal thoughts from the data layer."""

import json
from pathlib import Path
from typing import Any

from backend.knowledge.thought_adapter import ThoughtAdapter
from backend.knowledge.thought_engine import ThoughtEngine


class ThoughtLoader:
    """Load structured thought records into a ThoughtEngine."""

    def __init__(
        self,
        engine: ThoughtEngine | None = None,
    ) -> None:
        self.engine = engine or ThoughtEngine()

    def load_file(
        self,
        path: str | Path,
    ) -> int:
        """Load all thought records from one JSON file."""

        file_path = Path(path)

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data: Any = json.load(file)

        records: list[dict[str, Any]] = []

        if isinstance(data, list):

            records = [
                record
                for record in data
                if isinstance(record, dict)
            ]

        elif isinstance(data, dict):

            for value in data.values():

                if isinstance(value, list):

                    records.extend(
                        record
                        for record in value
                        if isinstance(record, dict)
                    )

        else:

            raise ValueError(
                f"Unsupported thought JSON structure "
                f"in {file_path}"
            )

        loaded = 0

        for record in records:

            thought = ThoughtAdapter.adapt(
                record
            )

            topic = (
                getattr(
                    thought,
                    "topic",
                    "",
                )
                or "general"
            )

            statement = (
                getattr(
                    thought,
                    "statement",
                    "",
                )
                or getattr(
                    thought,
                    "context",
                    "",
                )
                or ""
            )

            source = (
                getattr(
                    thought,
                    "source",
                    "",
                )
                or str(file_path)
            )

            confidence = getattr(
                thought,
                "confidence",
                None,
            )

            if confidence is None:
                confidence = 1.0

            evidence = getattr(
                thought,
                "evidence",
                None,
            )

            if evidence is None:
                evidence = []

            metadata: dict[str, Any] = {
                "source_file": str(
                    file_path
                ),
            }

            context = getattr(
                thought,
                "context",
                None,
            )

            if context:
                metadata["context"] = context

            thought_id = getattr(
                thought,
                "id",
                None,
            )

            if thought_id:
                metadata["thought_id"] = thought_id

            if not statement.strip():
                continue

            self.engine.add_documented_thought(

                topic=topic,

                statement=statement,

                source=source,

                confidence=float(
                    confidence
                ),

                evidence=list(
                    evidence
                ),

                metadata=metadata,
            )

            loaded += 1

        return loaded

    def load_directory(
        self,
        directory: str | Path,
    ) -> int:
        """Load all JSON thought files from a directory."""

        directory_path = Path(
            directory
        )

        if not directory_path.exists():
            return 0

        if not directory_path.is_dir():

            raise ValueError(
                f"Thought path is not a directory: "
                f"{directory_path}"
            )

        total = 0

        for path in sorted(
            directory_path.glob("*.json")
        ):

            total += self.load_file(
                path
            )

        return total

    def count(self) -> int:
        """Return the number of loaded thoughts."""

        return self.engine.count()