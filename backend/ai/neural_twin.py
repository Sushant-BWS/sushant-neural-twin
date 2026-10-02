"""Local Neural Twin orchestration layer."""

from pathlib import Path

from backend.ai.hallucination_guard import HallucinationGuard
from backend.ai.reasoning import (
    ReasoningEngine,
    ReasoningIntent,
    ReasoningRequest,
)
from backend.ai.retrieval import (
    SearchResult,
    SemanticRetriever,
)
from backend.ai.voice_client import (
    VoiceClient,
    VoiceServiceError,
)
from backend.knowledge.ingestion import (
    KnowledgeIngestionPipeline,
)
from backend.knowledge.resume_loader import (
    ResumeKnowledgeLoader,
)
from backend.knowledge.thought_engine import (
    ThoughtEngine,
)
from backend.knowledge.thought_loader import (
    ThoughtLoader,
)
from backend.ml.intent_classifier import (
    Intent,
    RuleBasedIntentClassifier,
)


class NeuralTwin:
    """Coordinate personal knowledge retrieval and grounded reasoning."""

    def __init__(self) -> None:
        # =====================================================
        # KNOWLEDGE
        # =====================================================

        self.ingestion = KnowledgeIngestionPipeline()

        self.retriever = SemanticRetriever()

        self.resume_loader = ResumeKnowledgeLoader()

        # =====================================================
        # THOUGHT MEMORY
        # =====================================================

        self.thought_engine = ThoughtEngine()

        self.thought_loader = ThoughtLoader(
            engine=self.thought_engine
        )

        # =====================================================
        # REASONING
        # =====================================================

        self.reasoning = ReasoningEngine()

        # =====================================================
        # SAFETY
        # =====================================================

        self.guard = HallucinationGuard()

        # =====================================================
        # VOICE
        # =====================================================

        self.voice_client = VoiceClient()

        # =====================================================
        # INTENT
        # =====================================================

        self.intent_classifier = (
            RuleBasedIntentClassifier()
        )

        # =====================================================
        # LOAD STATE
        # =====================================================

        self._knowledge_loaded = False
        self._thoughts_loaded = False
        self._resume_loaded = False

    # =========================================================
    # THOUGHT LOADING
    # =========================================================

    def load_thoughts(
        self,
        directory: str | Path = "data/thoughts",
    ) -> int:
        """Load documented thoughts into ThoughtEngine."""

        count = self.thought_loader.load_directory(
            directory
        )

        self._thoughts_loaded = True

        return count

    # =========================================================
    # KNOWLEDGE LOADING
    # =========================================================

    def load_knowledge(
        self,
        directory: str | Path = "data",
    ) -> int:
        """
        Load JSON knowledge and resume PDF knowledge
        into the same semantic retrieval index.
        """

        total_count = 0

        # -----------------------------------------------------
        # 1. Load existing JSON knowledge
        # -----------------------------------------------------

        documents = self.ingestion.ingest_directory(
            directory
        )

        if documents:
            total_count += (
                self.retriever.index_documents(
                    documents
                )
            )

        # -----------------------------------------------------
        # 2. Load resume PDF
        # -----------------------------------------------------

        resume_path = (
            Path(directory)
            / "resume"
            / "Sushant_Resume.pdf"
        )

        if resume_path.exists():
            resume_documents = (
                self.resume_loader.load(
                    resume_path
                )
            )

            if resume_documents:
                total_count += (
                    self.retriever.index_documents(
                        resume_documents
                    )
                )

            self._resume_loaded = True

        # -----------------------------------------------------
        # Mark knowledge as loaded
        # -----------------------------------------------------

        self._knowledge_loaded = True

        return total_count

    # =========================================================
    # INTENT CLASSIFICATION
    # =========================================================

    def classify_intent(
        self,
        question: str,
    ) -> Intent:
        """Classify a question using the local rule-based classifier."""

        prediction = (
            self.intent_classifier.classify(
                question
            )
        )

        return prediction.intent

    @staticmethod
    def _map_reasoning_intent(
        intent: Intent,
    ) -> ReasoningIntent:
        """Map classifier intent to reasoning intent."""

        mapping = {
            Intent.PROFILE: ReasoningIntent.PROFILE,
            Intent.EXPERIENCE: ReasoningIntent.EXPERIENCE,
            Intent.PROJECT: ReasoningIntent.PROJECT,
            Intent.SKILL: ReasoningIntent.SKILL,
            Intent.EDUCATION: ReasoningIntent.EDUCATION,
            Intent.CERTIFICATION: (
                ReasoningIntent.CERTIFICATION
            ),
            Intent.THOUGHT: ReasoningIntent.THOUGHT,
            Intent.DECISION: ReasoningIntent.DECISION,
            Intent.CAREER: ReasoningIntent.CAREER,
            Intent.RECRUITER: ReasoningIntent.RECRUITER,
            Intent.GENERAL: ReasoningIntent.GENERAL,
        }

        return mapping[intent]

    # =========================================================
    # INTENT-SPECIFIC SOURCE FILTERING
    # =========================================================

    @staticmethod
    def _document_matches_intent(
        document,
        intent: ReasoningIntent,
    ) -> bool:
        """
        Decide whether a knowledge document belongs to
        the requested reasoning intent.

        Both JSON sources and resume-derived documents
        are supported.
        """

        metadata = document.metadata or {}

        source = str(
            metadata.get(
                "source",
                "",
            )
        ).lower().replace(
            "\\",
            "/",
        )

        category = str(
            metadata.get(
                "category",
                "",
            )
        ).lower().strip()

        # -----------------------------------------------------
        # Resume knowledge
        # -----------------------------------------------------

        if category == "resume":
            category = str(
                metadata.get(
                    "resume_category",
                    "",
                )
            ).lower().strip()

        if source.startswith(
            "data/resume/"
        ):
            resume_mapping = {
                ReasoningIntent.PROFILE: {
                    "profile",
                },

                ReasoningIntent.EDUCATION: {
                    "education",
                },

                ReasoningIntent.SKILL: {
                    "skills",
                },

                ReasoningIntent.EXPERIENCE: {
                    "experience",
                },

                ReasoningIntent.PROJECT: {
                    "projects",
                },

                ReasoningIntent.RECRUITER: {
                    "profile",
                    "education",
                    "skills",
                    "experience",
                    "projects",
                    "achievements",
                },

                ReasoningIntent.GENERAL: {
                    "profile",
                    "education",
                    "skills",
                    "experience",
                    "projects",
                    "achievements",
                },
            }

            allowed_resume_categories = (
                resume_mapping.get(
                    intent,
                    set(),
                )
            )

            return (
                category
                in allowed_resume_categories
            )

        # -----------------------------------------------------
        # Existing JSON knowledge
        # -----------------------------------------------------

        source_groups = {
            ReasoningIntent.PROFILE: (
                "data/profile/",
                "data/achievements/",
            ),

            ReasoningIntent.EXPERIENCE: (
                "data/experience/",
            ),

            ReasoningIntent.PROJECT: (
                "data/projects/",
            ),

            ReasoningIntent.SKILL: (
                "data/skills/",
            ),

            ReasoningIntent.EDUCATION: (
                "data/education/",
            ),

            ReasoningIntent.CERTIFICATION: (
                "data/certifications/",
            ),

            ReasoningIntent.THOUGHT: (
                "data/thoughts/",
            ),

            ReasoningIntent.DECISION: (
                "data/thoughts/",
            ),

            ReasoningIntent.CAREER: (
                "data/experience/",
                "data/profile/",
            ),

            ReasoningIntent.RECRUITER: (
                "data/profile/",
                "data/experience/",
                "data/projects/",
                "data/skills/",
                "data/education/",
                "data/certifications/",
                "data/achievements/",
            ),

            ReasoningIntent.GENERAL: (
                "data/",
            ),
        }

        allowed_sources = source_groups.get(
            intent,
            (),
        )

        return any(
            source.startswith(prefix)
            for prefix in allowed_sources
        )

    # =========================================================
    # KNOWLEDGE RETRIEVAL
    # =========================================================

    def _retrieve_knowledge(
        self,
        question: str,
        intent: ReasoningIntent,
        top_k: int,
    ) -> list[SearchResult]:
        """
        Retrieve evidence from the complete local knowledge index,
        then filter it according to intent.
        """

        indexed_count = (
            self.retriever.count()
        )

        if indexed_count == 0:
            return []

        candidates = (
            self.retriever.retrieve(
                question,
                top_k=indexed_count,
            )
        )

        filtered: list[SearchResult] = []

        for result in candidates:
            if self._document_matches_intent(
                result.document,
                intent,
            ):
                filtered.append(result)

        return filtered[:top_k]

    # =========================================================
    # THOUGHT RETRIEVAL
    # =========================================================

    def _retrieve_thoughts(
        self,
        question: str,
        intent: ReasoningIntent,
        top_k: int,
    ):
        """
        Retrieve documented thoughts only for thought-oriented
        questions.
        """

        if intent not in {
            ReasoningIntent.THOUGHT,
            ReasoningIntent.DECISION,
        }:
            return []

        results = self.thought_engine.search(
            question,
            limit=top_k,
        )

        unique_results = []

        seen_sources: set[str] = set()

        for result in results:
            source = (
                result.thought.source
                .strip()
                .lower()
            )

            if source in seen_sources:
                continue

            seen_sources.add(source)
            unique_results.append(result)

        return unique_results[:top_k]

    # =========================================================
    # MAIN QUESTION PIPELINE
    # =========================================================

    def ask(
        self,
        question: str,
        intent: ReasoningIntent | None = None,
        top_k: int = 3,
        generate_voice: bool = True,
    ):
        """
        Answer a question using grounded personal knowledge.

        Parameters
        ----------
        question:
            User question.

        intent:
            Optional manually supplied reasoning intent.

        top_k:
            Maximum number of evidence records.

        generate_voice:
            If True, generate voice synchronously.
            If False, return text only.

            The Chat API uses False and handles voice
            generation as a background task.
        """

        # =====================================================
        # VALIDATE
        # =====================================================

        if not question.strip():
            raise ValueError(
                "question must not be empty"
            )

        if top_k < 1:
            raise ValueError(
                "top_k must be at least 1"
            )

        # =====================================================
        # LOAD THOUGHTS
        # =====================================================

        if not self._thoughts_loaded:
            self.load_thoughts()

        # =====================================================
        # LOAD KNOWLEDGE
        # =====================================================

        if not self._knowledge_loaded:
            self.load_knowledge()

        # =====================================================
        # DETECT INTENT
        # =====================================================

        if intent is None:

            detected_intent = (
                self.classify_intent(
                    question
                )
            )

            intent = (
                self._map_reasoning_intent(
                    detected_intent
                )
            )

        # =====================================================
        # REASONING REQUEST
        # =====================================================

        request = ReasoningRequest(
            question=question,
            intent=intent,
        )

        # =====================================================
        # KNOWLEDGE RETRIEVAL
        # =====================================================

        knowledge_results = (
            self._retrieve_knowledge(
                question=question,
                intent=intent,
                top_k=top_k,
            )
        )

        # =====================================================
        # THOUGHT RETRIEVAL
        # =====================================================

        thought_results = (
            self._retrieve_thoughts(
                question=question,
                intent=intent,
                top_k=top_k,
            )
        )

        # =====================================================
        # REASON
        # =====================================================

        reasoning_response = (
            self.reasoning.reason(
                request=request,
                facts=knowledge_results,
                thoughts=thought_results,
            )
        )

        # =====================================================
        # EVIDENCE
        # =====================================================

        evidence = [
            *knowledge_results,
            *thought_results,
        ]

        # =====================================================
        # HALLUCINATION PROTECTION
        # =====================================================

        guarded = self.guard.guard_answer(
            reasoning_response.answer,
            evidence,
        )

        # =====================================================
        # VOICE
        # =====================================================

        audio_file = None
        voice_error = None

        # IMPORTANT:
        # The Chat API calls ask(..., generate_voice=False)
        # so it does NOT wait for Chatterbox.
        #
        # Direct callers can still use the default
        # generate_voice=True behaviour.

        if (
            generate_voice
            and guarded.safe
            and guarded.answer
        ):

            try:

                audio_file = (
                    self.voice_client.synthesize(
                        guarded.answer
                    )
                )

            except VoiceServiceError as exc:

                voice_error = str(
                    exc
                )

        # =====================================================
        # FINAL RESPONSE
        # =====================================================

        return {
            "answer": guarded.answer,

            "safe": guarded.safe,

            "intent": intent.value,

            "reasoning_summary": (
                reasoning_response.reasoning_summary
            ),

            "evidence_count": (
                reasoning_response.evidence_count
            ),

            "verifications": [
                verification.model_dump()
                for verification
                in guarded.verifications
            ],

            "audio_file": audio_file,

            "voice_error": voice_error,
        }