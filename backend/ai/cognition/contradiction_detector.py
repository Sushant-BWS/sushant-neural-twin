"""Detects conflicting facts and marks them as issues to resolve with priority rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ContradictionRecord:
    """A detected conflict between two assertions."""

    source_a: str
    source_b: str
    claim_a: str
    claim_b: str
    explanation: str


class ContradictionDetector:
    """Flags contradictions that need human-readable resolution."""

    @staticmethod
    def detect(claims: list[tuple[str, str]]) -> list[ContradictionRecord]:
        conflicts: list[ContradictionRecord] = []
        seen: set[tuple[str, str]] = set()
        for index, (source_a, claim_a) in enumerate(claims):
            for source_b, claim_b in claims[index + 1:]:
                if claim_a.lower().strip() == claim_b.lower().strip():
                    continue
                pair = tuple(sorted([(source_a, claim_a), (source_b, claim_b)]))
                if pair in seen:
                    continue
                seen.add(pair)
                conflicts.append(
                    ContradictionRecord(
                        source_a=source_a,
                        source_b=source_b,
                        claim_a=claim_a,
                        claim_b=claim_b,
                        explanation="CONFLICT DETECTED: Source A and Source B disagree; source priority and recency may determine the final answer.",
                    )
                )
        return conflicts
