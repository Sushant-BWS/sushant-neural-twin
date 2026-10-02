import unittest

from backend.ai.cognition.cognitive_engine import CognitiveEngine
from backend.events import EventBus, UserMessageReceived
from backend.knowledge.quality import KnowledgeQuality
from backend.memory.memory_manager import MemoryManager


class ArchitectureLayerTests(unittest.TestCase):
    def test_cognitive_engine_process_returns_summary(self):
        engine = CognitiveEngine()
        result = engine.process("Tell me about the assistant", history=["Previous message"])
        self.assertIn("answer", result)
        self.assertIn("summary", result)

    def test_memory_manager_decide_uses_retrieval_signals(self):
        manager = MemoryManager()
        result = manager.decide("profile", "What are your strengths?")
        self.assertIsInstance(result, list)
        self.assertTrue(result)

    def test_event_bus_routes_events(self):
        bus = EventBus()
        seen = []

        def handler(event):
            seen.append(event.event_type)

        bus.subscribe("user_message_received", handler)
        bus.publish(UserMessageReceived(payload={"message": "hi"}))
        self.assertEqual(seen, ["user_message_received"])

    def test_knowledge_quality_uses_conservative_threshold(self):
        result = KnowledgeQuality.validate("resume", "This item has enough information to be useful.", {"confidence": 0.8, "source_type": "resume"})
        self.assertTrue(result.passed)
        self.assertGreaterEqual(result.score, 0.8)


if __name__ == "__main__":
    unittest.main()
