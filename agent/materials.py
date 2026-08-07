from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import bm25s

from sdk._core.v0.material_catalog import MaterialCatalogEntry, load_material_entries

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(value: str) -> list[str]:
    return _TOKEN_RE.findall(value.lower())


@dataclass(frozen=True)
class MaterialSearchMatch:
    entry: MaterialCatalogEntry
    score: float
    match_quality: str


@dataclass(frozen=True)
class _MaterialSearchIndex:
    entries: tuple[MaterialCatalogEntry, ...]
    retriever: bm25s.BM25


@lru_cache(maxsize=1)
def load_material_search_index() -> _MaterialSearchIndex:
    entries = load_material_entries()
    corpus: list[list[str]] = []
    for entry in entries:
        name = _tokens(entry.name)
        description = _tokens(entry.description)
        tags = [token for value in entry.tags for token in _tokens(value)]
        aliases = [token for value in entry.aliases for token in _tokens(value)]
        catalog = _tokens(entry.catalog_id)
        corpus.append(name * 6 + aliases * 5 + tags * 4 + description * 2 + catalog)
    retriever = bm25s.BM25()
    if corpus:
        retriever.index(corpus, show_progress=False)
    return _MaterialSearchIndex(entries=entries, retriever=retriever)


def search_materials(
    query: str,
    *,
    catalog: str | None = None,
    limit: int = 5,
) -> list[MaterialSearchMatch]:
    query_tokens = _tokens(query)
    if not query_tokens or limit < 1:
        return []
    index = load_material_search_index()
    candidates = [
        position
        for position, entry in enumerate(index.entries)
        if catalog is None or entry.catalog_id == catalog
    ]
    if not candidates:
        return []
    candidate_k = min(len(candidates), max(limit * 4, 12))
    retrieval = index.retriever.retrieve(
        [query_tokens],
        k=candidate_k,
        corpus=candidates,
        show_progress=False,
    )
    matches: list[MaterialSearchMatch] = []
    for raw_index, raw_score in zip(retrieval.documents[0], retrieval.scores[0], strict=True):
        score = float(raw_score)
        if score <= 0:
            continue
        entry = index.entries[int(raw_index)]
        entry_text = " ".join([entry.name, entry.description, *entry.tags, *entry.aliases]).lower()
        matched_count = sum(token in entry_text for token in set(query_tokens))
        quality = "strong" if matched_count >= min(2, len(set(query_tokens))) else "weak"
        matches.append(MaterialSearchMatch(entry=entry, score=score, match_quality=quality))
        if len(matches) >= limit:
            break
    return matches


__all__ = ["MaterialSearchMatch", "load_material_search_index", "search_materials"]
