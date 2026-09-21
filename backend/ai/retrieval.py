"""Local vector indexing and semantic retrieval interfaces."""

from collections.abc import Iterable
import math
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from backend.ai.embeddings import EmbeddingProvider, HashEmbeddingProvider
from backend.knowledge.store import KnowledgeDocument


class SearchResult(BaseModel):
	"""A retrieved document and its similarity score."""

	model_config = ConfigDict(frozen=True)

	document: KnowledgeDocument
	score: float = Field(ge=-1, le=1)


@runtime_checkable
class VectorIndex(Protocol):
	"""Interface for replaceable local or persistent vector indexes."""

	def add(self, documents: Iterable[KnowledgeDocument]) -> int:
		"""Embed and store documents, returning the number accepted."""
		...

	def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
		"""Return the most similar documents for a query."""
		...

	def count(self) -> int:
		"""Return the number of indexed documents."""
		...


class InMemoryVectorIndex:
	"""Dependency-free vector index for local development."""

	def __init__(self, provider: EmbeddingProvider | None = None) -> None:
		self.provider = provider or HashEmbeddingProvider()
		self._documents: dict[str, KnowledgeDocument] = {}
		self._vectors: dict[str, list[float]] = {}

	def add(self, documents: Iterable[KnowledgeDocument]) -> int:
		"""Embed and store documents by stable document ID."""

		accepted = 0
		for document in documents:
			vector = self.provider.embed(document.content)
			self._validate_vector(vector)
			self._documents[document.id] = document
			self._vectors[document.id] = vector
			accepted += 1
		return accepted

	def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
		"""Return documents ordered by descending cosine similarity."""

		if top_k < 1:
			raise ValueError("top_k must be at least 1")
		query_vector = self.provider.embed(query)
		self._validate_vector(query_vector)
		ranked = [
			SearchResult(
				document=self._documents[document_id],
				score=self._cosine(query_vector, vector),
			)
			for document_id, vector in self._vectors.items()
		]
		ranked.sort(key=lambda result: (-result.score, result.document.id))
		return ranked[:top_k]

	def count(self) -> int:
		"""Return the number of uniquely indexed documents."""

		return len(self._documents)

	def _validate_vector(self, vector: list[float]) -> None:
		if len(vector) != self.provider.dimension:
			raise ValueError("embedding provider returned an unexpected dimension")

	@staticmethod
	def _cosine(left: list[float], right: list[float]) -> float:
		left_norm = math.sqrt(sum(value * value for value in left))
		right_norm = math.sqrt(sum(value * value for value in right))
		if not left_norm or not right_norm:
			return 0.0
		return max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)))


class SemanticRetriever:
	"""Coordinate indexing and top-k semantic retrieval."""

	def __init__(self, index: VectorIndex | None = None) -> None:
		self.index = index or InMemoryVectorIndex()

	def index_documents(self, documents: Iterable[KnowledgeDocument]) -> int:
		"""Add normalized knowledge documents to the vector index."""

		return self.index.add(documents)

	def retrieve(self, query: str, top_k: int = 5) -> list[SearchResult]:
		"""Retrieve the most semantically similar documents."""

		if not query.strip():
			return []
		return self.index.search(query, top_k)

	def count(self) -> int:
		"""Return the number of indexed documents."""

		return self.index.count()
