"""Tests for the Phase 3 knowledge ingestion boundary."""

import json
import tempfile
import unittest
from pathlib import Path

from backend.knowledge.ingestion import (
    DataLoader,
    DocumentParser,
    JsonValidator,
    KnowledgeIngestionPipeline,
    MetadataExtractor,
)
from backend.knowledge.schemas import Skill
from backend.knowledge.store import InMemoryKnowledgeIndex


class KnowledgeIngestionTests(unittest.TestCase):
    """Verify loading, validation, normalization, and indexing behavior."""

    def test_ingests_valid_json_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "skills.json"
            source.write_text(
                json.dumps([{"name": "  Python  "}, {"name": "FastAPI"}]),
                encoding="utf-8",
            )
            pipeline = KnowledgeIngestionPipeline(
                parser=DocumentParser(metadata_extractor=MetadataExtractor(root))
            )

            documents = pipeline.ingest_file(source, Skill)

            self.assertEqual(len(documents), 2)
            self.assertEqual(documents[0].metadata["source"], "skills.json")
            self.assertEqual(documents[0].metadata["record_index"], 0)
            self.assertIn('"name": "Python"', documents[0].content)

    def test_rejects_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "invalid.json"
            source.write_text("{invalid", encoding="utf-8")

            with self.assertRaises(ValueError):
                DataLoader().load_json(source)

    def test_indexes_ingested_documents(self) -> None:
        documents = DocumentParser().parse(
            [{"name": "Python"}, {"name": "FastAPI"}],
            "skills.json",
            Skill,
        )
        index = InMemoryKnowledgeIndex()

        accepted = index.add(documents)

        self.assertEqual(accepted, 2)
        self.assertEqual(index.count(), 2)

    def test_empty_json_collections_validate(self) -> None:
        self.assertEqual(JsonValidator().validate([], Skill), [])


if __name__ == "__main__":
    unittest.main()
