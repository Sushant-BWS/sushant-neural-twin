"""Replaceable local AI subsystem components."""

from backend.ai.embeddings import EmbeddingProvider, HashEmbeddingProvider
from backend.ai.llm import (
	GenerationRequest,
	GenerationResponse,
	LLMProvider,
	LocalDevelopmentProvider,
	generate_text,
)
from backend.ai.hallucination_guard import (
	ClaimEvidence,
	ClaimStatus,
	ClaimVerification,
	GuardedAnswer,
	HallucinationGuard,
)
from backend.ai.reranker import LexicalReranker
from backend.ai.reasoning import (
	EvidenceReference,
	ReasoningEngine,
	ReasoningIntent,
	ReasoningRequest,
	ReasoningResponse,
)
from backend.ai.retrieval import (
	InMemoryVectorIndex,
	SearchResult,
	SemanticRetriever,
	VectorIndex,
)

__all__ = [
	"EmbeddingProvider",
	"ClaimEvidence",
	"ClaimStatus",
	"ClaimVerification",
	"GenerationRequest",
	"GenerationResponse",
	"GuardedAnswer",
	"HallucinationGuard",
	"HashEmbeddingProvider",
	"InMemoryVectorIndex",
	"LLMProvider",
	"LexicalReranker",
	"LocalDevelopmentProvider",
	"EvidenceReference",
	"ReasoningEngine",
	"ReasoningIntent",
	"ReasoningRequest",
	"ReasoningResponse",
	"SearchResult",
	"SemanticRetriever",
	"VectorIndex",
	"generate_text",
]
