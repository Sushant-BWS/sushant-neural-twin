"""Tests for the Phase 5 local semantic retrieval boundary."""

import unittest

from backend.ai import (
    HashEmbeddingProvider,
    InMemoryVectorIndex,
    LexicalReranker,
    SemanticRetriever,
)
from backend.knowledge.store import KnowledgeDocument


class RetrievalTests(unittest.TestCase):
    """Verify embedding, indexing, retrieval, and reranking behavior."""

    def setUp(self) -> None:
        self.index = InMemoryVectorIndex(HashEmbeddingProvider(dimension=128))
        self.documents = [
            KnowledgeDocument(
                id="python",
                content="Python backend engineering",
                metadata={"source": "projects.json#0"},
            ),
            KnowledgeDocument(
                id="cloud",
                content="Cloud deployment operations",
                metadata={"source": "projects.json#1"},
            ),
            KnowledgeDocument(
                id="testing",
                content="Python testing practices",
                metadata={"source": "skills.json#0"},
            ),
        ]

    def test_embedding_is_deterministic_and_normalized(self) -> None:
        provider = HashEmbeddingProvider(dimension=64)

        vector = provider.embed("Python backend")

        self.assertEqual(vector, provider.embed("Python backend"))
        self.assertEqual(len(vector), 64)
        self.assertAlmostEqual(sum(value * value for value in vector), 1.0)

    def test_retrieval_returns_relevant_documents(self) -> None:
        self.index.add(self.documents)

        results = self.index.search("Python backend", top_k=2)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].document.id, "python")
        self.assertGreaterEqual(results[0].score, results[1].score)

    def test_retriever_rejects_invalid_top_k_and_empty_queries(self) -> None:
        retriever = SemanticRetriever(self.index)
        self.assertEqual(retriever.retrieve("   "), [])
        with self.assertRaises(ValueError):
            self.index.search("Python", top_k=0)

    def test_duplicate_documents_replace_existing_vectors(self) -> None:
        self.index.add(self.documents)
        self.index.add(
            [KnowledgeDocument(id="python", content="Replacement Python", metadata={})]
        )

        self.assertEqual(self.index.count(), 3)
        self.assertEqual(self.index.search("Replacement", top_k=1)[0].document.id, "python")

    def test_reranker_prioritizes_token_overlap(self) -> None:
        self.index.add(self.documents)
        candidates = self.index.search("Python backend", top_k=3)

        reranked = LexicalReranker().rerank("Python backend", candidates)

        self.assertEqual(reranked[0].document.id, "python")


if __name__ == "__main__":
    unittest.main()
