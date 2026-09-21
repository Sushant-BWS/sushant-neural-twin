"""Replaceable local text embedding interfaces and implementation."""

from collections.abc import Iterable
import hashlib
import math
import re
from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
	"""Interface for replaceable text embedding providers."""

	dimension: int

	def embed(self, text: str) -> list[float]:
		"""Return a fixed-size vector for one text value."""
		...

	def embed_many(self, texts: Iterable[str]) -> list[list[float]]:
		"""Return vectors for multiple text values."""
		...


class HashEmbeddingProvider:
	"""Deterministic token feature hashing for local development."""

	_token_pattern = re.compile(r"[a-z0-9]+")

	def __init__(self, dimension: int = 256) -> None:
		if dimension < 2:
			raise ValueError("dimension must be at least 2")
		self.dimension = dimension

	def embed(self, text: str) -> list[float]:
		"""Create a unit-normalized vector from hashed word features."""

		if not isinstance(text, str):
			raise TypeError("text must be a string")

		vector = [0.0] * self.dimension
		tokens = self._token_pattern.findall(text.lower())
		for token in tokens:
			digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
			bucket = int.from_bytes(digest[:4], "big") % self.dimension
			sign = 1.0 if digest[4] & 1 else -1.0
			vector[bucket] += sign

		magnitude = math.sqrt(sum(value * value for value in vector))
		if magnitude:
			vector = [value / magnitude for value in vector]
		return vector

	def embed_many(self, texts: Iterable[str]) -> list[list[float]]:
		"""Create vectors for an iterable of text values."""

		return [self.embed(text) for text in texts]
