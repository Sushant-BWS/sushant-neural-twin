"""Load, validate, normalize, and prepare knowledge documents."""

from collections.abc import Callable, Iterable, Mapping
from json import JSONDecodeError
from pathlib import Path
from typing import Any
import json
import re

from pydantic import BaseModel

from backend.knowledge.store import KnowledgeDocument, KnowledgeIndex

SchemaType = type[BaseModel]
SchemaResolver = Callable[[Path], SchemaType | None]


class DataLoader:
    """Load raw JSON data from the project data layer."""

    def load_json(self, path: str | Path) -> Any:
        """Read and decode one JSON file."""

        file_path = Path(path)
        if file_path.suffix.lower() != ".json":
            raise ValueError(f"Expected a JSON file: {file_path}")

        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except JSONDecodeError as error:
            raise ValueError(f"Invalid JSON in {file_path}: {error.msg}") from error

    def json_files(self, directory: str | Path) -> list[Path]:
        """Return JSON files below a directory in deterministic order."""

        return sorted(Path(directory).rglob("*.json"))


class JsonValidator:
    """Validate decoded JSON against an optional Pydantic model."""

    def validate(self, payload: Any, schema: SchemaType | None = None) -> Any:
        """Validate one object or a collection of objects."""

        if schema is None:
            return payload
        if isinstance(payload, list):
            return [schema.model_validate(item) for item in payload]
        if isinstance(payload, dict):
            return schema.model_validate(payload)
        raise ValueError("Knowledge JSON must contain an object or an array")

    def validate_file(
        self,
        path: str | Path,
        schema: SchemaType | None = None,
    ) -> Any:
        """Load and validate one JSON file."""

        payload = DataLoader().load_json(path)
        return self.validate(payload, schema)


class TextNormalizer:
    """Convert records into stable, whitespace-normalized text."""

    _whitespace = re.compile(r"\s+")

    def normalize(self, value: Any) -> str:
        """Serialize a value and collapse irrelevant whitespace."""

        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json", exclude_none=True)
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        return self._whitespace.sub(" ", value).strip()


class MetadataExtractor:
    """Extract source metadata without inferring personal information."""

    def __init__(self, data_root: str | Path | None = None) -> None:
        self.data_root = Path(data_root).resolve() if data_root else None

    def extract(
        self,
        path: str | Path,
        record_index: int | None = None,
        schema: SchemaType | None = None,
    ) -> dict[str, Any]:
        """Return source, content type, and optional record metadata."""

        source_path = Path(path).resolve()
        if self.data_root:
            try:
                source = source_path.relative_to(self.data_root)
            except ValueError:
                source = source_path
        else:
            source = Path(path)

        metadata: dict[str, Any] = {
            "source": source.as_posix(),
            "content_type": "application/json",
        }
        if record_index is not None:
            metadata["record_index"] = record_index
        if schema is not None:
            metadata["schema"] = schema.__name__
        return metadata


class DocumentParser:
    """Turn validated JSON records into normalized knowledge documents."""

    def __init__(
        self,
        normalizer: TextNormalizer | None = None,
        metadata_extractor: MetadataExtractor | None = None,
    ) -> None:
        self.normalizer = normalizer or TextNormalizer()
        self.metadata_extractor = metadata_extractor or MetadataExtractor()

    def parse(
        self,
        payload: Any,
        source_path: str | Path,
        schema: SchemaType | None = None,
    ) -> list[KnowledgeDocument]:
        """Create one document per object in a JSON object or array."""

        records = payload if isinstance(payload, list) else [payload]
        documents: list[KnowledgeDocument] = []
        source = Path(source_path).as_posix()
        is_collection = isinstance(payload, list)

        for index, record in enumerate(records):
            suffix = f"#{index}" if is_collection else ""
            documents.append(
                KnowledgeDocument(
                    id=f"{source}{suffix}",
                    content=self.normalizer.normalize(record),
                    metadata=self.metadata_extractor.extract(
                        source_path,
                        record_index=index if is_collection else None,
                        schema=schema,
                    ),
                )
            )
        return documents


class KnowledgeIngestionPipeline:
    """Coordinate loading, validation, parsing, and optional indexing."""

    def __init__(
        self,
        loader: DataLoader | None = None,
        validator: JsonValidator | None = None,
        parser: DocumentParser | None = None,
    ) -> None:
        self.loader = loader or DataLoader()
        self.validator = validator or JsonValidator()
        self.parser = parser or DocumentParser()

    def ingest_file(
        self,
        path: str | Path,
        schema: SchemaType | None = None,
    ) -> list[KnowledgeDocument]:
        """Ingest one JSON file into normalized documents."""

        raw_payload = self.loader.load_json(path)
        validated_payload = self.validator.validate(raw_payload, schema)
        return self.parser.parse(validated_payload, path, schema)

    def ingest_directory(
        self,
        directory: str | Path,
        schema_resolver: SchemaResolver | Mapping[str, SchemaType] | None = None,
    ) -> list[KnowledgeDocument]:
        """Ingest all JSON files below a directory."""

        documents: list[KnowledgeDocument] = []
        for path in self.loader.json_files(directory):
            schema = self._resolve_schema(path, schema_resolver)
            documents.extend(self.ingest_file(path, schema))
        return documents

    def ingest_to(
        self,
        paths: Iterable[str | Path],
        index: KnowledgeIndex,
        schema_resolver: SchemaResolver | Mapping[str, SchemaType] | None = None,
    ) -> int:
        """Ingest files and add their documents to a supplied index."""

        documents: list[KnowledgeDocument] = []
        for path in paths:
            schema = self._resolve_schema(Path(path), schema_resolver)
            documents.extend(self.ingest_file(path, schema))
        return index.add(documents)

    @staticmethod
    def _resolve_schema(
        path: Path,
        resolver: SchemaResolver | Mapping[str, SchemaType] | None,
    ) -> SchemaType | None:
        if resolver is None:
            return None
        if callable(resolver):
            return resolver(path)
        return resolver.get(path.name)
