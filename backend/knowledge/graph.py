"""Source-aware knowledge graph interfaces and local implementation."""

from collections.abc import Iterable
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class EntityType(StrEnum):
	"""Supported entity categories in the personal knowledge graph."""

	PERSON = "Person"
	SKILL = "Skill"
	PROJECT = "Project"
	TECHNOLOGY = "Technology"
	EXPERIENCE = "Experience"
	EDUCATION = "Education"
	CERTIFICATION = "Certification"
	THOUGHT = "Thought"
	CAREER_EVENT = "CareerEvent"


class GraphEntity(BaseModel):
	"""An explicitly documented entity in the graph."""

	model_config = ConfigDict(extra="forbid", frozen=True)

	id: str = Field(min_length=1)
	entity_type: EntityType
	label: str = Field(min_length=1)
	source_refs: list[str] = Field(min_length=1)
	properties: dict[str, Any] = Field(default_factory=dict)


class GraphRelationship(BaseModel):
	"""A directed, source-backed relationship between two entities."""

	model_config = ConfigDict(extra="forbid", frozen=True)

	source_id: str = Field(min_length=1)
	target_id: str = Field(min_length=1)
	relation: str = Field(min_length=1)
	source_refs: list[str] = Field(min_length=1)
	confidence: float | None = Field(default=None, ge=0, le=1)
	properties: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class KnowledgeGraph(Protocol):
	"""Interface for replaceable graph implementations."""

	def add_entity(self, entity: GraphEntity) -> GraphEntity:
		"""Add or replace an entity by ID."""
		...

	def add_relationship(self, relationship: GraphRelationship) -> GraphRelationship:
		"""Add a relationship between existing entities."""
		...

	def get_entity(self, entity_id: str) -> GraphEntity | None:
		"""Return an entity by ID when it exists."""
		...

	def relationships(self, entity_id: str | None = None) -> list[GraphRelationship]:
		"""Return relationships, optionally limited to one entity."""
		...

	def neighbors(self, entity_id: str) -> list[GraphEntity]:
		"""Return directly connected entities in deterministic order."""
		...

	def entity_count(self) -> int:
		"""Return the number of entities."""
		...

	def relationship_count(self) -> int:
		"""Return the number of relationships."""
		...


class InMemoryKnowledgeGraph:
	"""Local graph implementation with no persistence or inferred edges."""

	def __init__(self) -> None:
		self._entities: dict[str, GraphEntity] = {}
		self._relationships: dict[tuple[str, str, str], GraphRelationship] = {}

	def add_entity(self, entity: GraphEntity) -> GraphEntity:
		"""Add or replace an explicitly documented entity."""

		self._entities[entity.id] = entity
		return entity

	def add_entities(self, entities: Iterable[GraphEntity]) -> int:
		"""Add multiple entities and return the number accepted."""

		accepted = 0
		for entity in entities:
			self.add_entity(entity)
			accepted += 1
		return accepted

	def add_relationship(self, relationship: GraphRelationship) -> GraphRelationship:
		"""Add an edge only when both endpoint entities already exist."""

		if relationship.source_id not in self._entities:
			raise ValueError(f"Unknown source entity: {relationship.source_id}")
		if relationship.target_id not in self._entities:
			raise ValueError(f"Unknown target entity: {relationship.target_id}")
		key = (relationship.source_id, relationship.target_id, relationship.relation)
		self._relationships[key] = relationship
		return relationship

	def add_relationships(self, relationships: Iterable[GraphRelationship]) -> int:
		"""Add multiple explicit relationships and return the number accepted."""

		accepted = 0
		for relationship in relationships:
			self.add_relationship(relationship)
			accepted += 1
		return accepted

	def get_entity(self, entity_id: str) -> GraphEntity | None:
		"""Return an entity by ID when it exists."""

		return self._entities.get(entity_id)

	def relationships(self, entity_id: str | None = None) -> list[GraphRelationship]:
		"""Return relationships in insertion order, optionally filtered."""

		relationships = list(self._relationships.values())
		if entity_id is None:
			return relationships
		return [
			relationship
			for relationship in relationships
			if entity_id in (relationship.source_id, relationship.target_id)
		]

	def neighbors(self, entity_id: str) -> list[GraphEntity]:
		"""Return directly connected entities ordered by entity ID."""

		neighbor_ids = {
			relationship.target_id
			for relationship in self.relationships(entity_id)
			if relationship.source_id == entity_id
		}
		neighbor_ids.update(
			relationship.source_id
			for relationship in self.relationships(entity_id)
			if relationship.target_id == entity_id
		)
		return [self._entities[neighbor_id] for neighbor_id in sorted(neighbor_ids)]

	def entity_count(self) -> int:
		"""Return the number of entities."""

		return len(self._entities)

	def relationship_count(self) -> int:
		"""Return the number of relationships."""

		return len(self._relationships)
