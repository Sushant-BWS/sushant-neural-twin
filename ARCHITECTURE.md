# Architecture Notes

This project is intentionally built as a local-first cognitive assistant that keeps a strong compatibility layer above the original application.

## Runtime model

- Python 3.11 local runtime
- CPU-only execution by default
- FastAPI service shell with local retrieval and memory
- Observability, auth, and CORS remain available for local deployments

## Layers

1. API layer
   - health, ready, metrics, chat, recruiter, and memory endpoints
2. Service layer
   - stable façade objects for chat, memory, conversation, recruiting, and voice
3. Cognitive layer
   - query planning, confidence, contradiction detection, evidence packaging, and response shaping
4. Knowledge layer
   - retrieval, graph, ingestion, quality validation, and provenance
5. Memory layer
   - short-term, long-term, episodic, and working-memory management
6. Event layer
   - lightweight event bus for local orchestration

## Safety principles

- No hidden chain-of-thought is exposed to clients
- Reasoning summaries remain observable and explainable
- Local-first execution avoids GPU or remote model assumptions
- Backward compatibility is preserved before new abstractions are added
