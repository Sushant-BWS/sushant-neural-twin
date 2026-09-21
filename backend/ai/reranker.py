"""Deterministic reranking for retrieved local knowledge candidates."""

from collections.abc import Iterable
import re

from backend.ai.retrieval import SearchResult


class LexicalReranker:
	"""Blend semantic scores with query-token overlap."""

	_token_pattern = re.compile(r"[a-z0-9]+")

	def rerank(
		self,
		query: str,
		results: Iterable[SearchResult],
		top_k: int | None = None,
	) -> list[SearchResult]:
		"""Return candidates ordered by a transparent blended score."""

		query_tokens = set(self._token_pattern.findall(query.lower()))
		ranked: list[tuple[float, SearchResult]] = []
		for result in results:
			content_tokens = set(
				self._token_pattern.findall(result.document.content.lower())
			)
			overlap = len(query_tokens & content_tokens) / max(len(query_tokens), 1)
			blended_score = (result.score * 0.8) + (overlap * 0.2)
			ranked.append((blended_score, result))

		ranked.sort(key=lambda item: (-item[0], item[1].document.id))
		reranked = [result for _, result in ranked]
		return reranked if top_k is None else reranked[:top_k]
