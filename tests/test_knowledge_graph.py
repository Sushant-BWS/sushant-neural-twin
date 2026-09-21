"""Tests for the Phase 8 source-aware knowledge graph."""

import unittest

from backend.knowledge import (
    EntityType,
    GraphEntity,
    GraphRelationship,
    InMemoryKnowledgeGraph,
    KnowledgeGraph,
)


class KnowledgeGraphTests(unittest.TestCase):
    """Verify explicit, source-backed graph behavior."""

    def setUp(self) -> None:
        self.graph = InMemoryKnowledgeGraph()
        self.person = GraphEntity(
            id="person",
            entity_type=EntityType.PERSON,
            label="Sushant Neural Twin",
            source_refs=["profile/profile.json"],
        )
        self.project = GraphEntity(
            id="project-1",
            entity_type=EntityType.PROJECT,
            label="Documented Project",
            source_refs=["projects/projects.json#0"],
        )
        self.skill = GraphEntity(
            id="skill-python",
            entity_type=EntityType.SKILL,
            label="Python",
            source_refs=["profile/skills.json#0"],
        )
        self.graph.add_entities([self.person, self.project, self.skill])

    def test_implementation_satisfies_graph_contract(self) -> None:
        self.assertIsInstance(self.graph, KnowledgeGraph)
        self.assertEqual(self.graph.entity_count(), 3)
        self.assertEqual(self.graph.relationship_count(), 0)

    def test_adds_source_backed_relationships_and_traverses_neighbors(self) -> None:
        worked_on = GraphRelationship(
            source_id="person",
            target_id="project-1",
            relation="worked_on",
            source_refs=["projects/projects.json#0"],
            confidence=0.9,
        )
        uses_skill = GraphRelationship(
            source_id="project-1",
            target_id="skill-python",
            relation="uses",
            source_refs=["projects/projects.json#0"],
        )

        self.graph.add_relationships([worked_on, uses_skill])

        self.assertEqual(self.graph.relationship_count(), 2)
        self.assertEqual([entity.id for entity in self.graph.neighbors("person")], ["project-1"])
        self.assertEqual(
            [entity.id for entity in self.graph.neighbors("project-1")],
            ["person", "skill-python"],
        )
        self.assertEqual(self.graph.relationships("project-1"), [worked_on, uses_skill])

    def test_duplicate_relationship_replaces_existing_edge(self) -> None:
        original = GraphRelationship(
            source_id="person",
            target_id="project-1",
            relation="worked_on",
            source_refs=["source-a"],
            confidence=0.5,
        )
        replacement = original.model_copy(update={"source_refs": ["source-b"]})

        self.graph.add_relationship(original)
        self.graph.add_relationship(replacement)

        self.assertEqual(self.graph.relationship_count(), 1)
        self.assertEqual(self.graph.relationships()[0].source_refs, ["source-b"])

    def test_rejects_unknown_endpoints(self) -> None:
        relationship = GraphRelationship(
            source_id="missing",
            target_id="project-1",
            relation="worked_on",
            source_refs=["projects/projects.json#0"],
        )

        with self.assertRaises(ValueError):
            self.graph.add_relationship(relationship)

    def test_requires_provenance_for_entities_and_relationships(self) -> None:
        with self.assertRaises(ValueError):
            GraphEntity(
                id="unverified",
                entity_type=EntityType.PROJECT,
                label="Unverified",
                source_refs=[],
            )
        with self.assertRaises(ValueError):
            GraphRelationship(
                source_id="person",
                target_id="project-1",
                relation="worked_on",
                source_refs=[],
            )

    def test_does_not_infer_relationships(self) -> None:
        self.assertEqual(self.graph.relationship_count(), 0)
        self.assertEqual(self.graph.neighbors("person"), [])


if __name__ == "__main__":
    unittest.main()
