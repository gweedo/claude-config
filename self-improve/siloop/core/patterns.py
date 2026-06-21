"""pattern_key similarity — the default PatternMatcher (PROTOCOL §5).

The count is the whole point of the loop, so a new key is guarded: `is_known` decides
acceptance, `suggest_keys` returns the closest existing keys when it is rejected. Matching
combines tokenized-kebab Jaccard (catches reordered / synonym-free near-dups like
`raw-sql-in-router` vs `sql-in-handler`) with edit-distance ratio (catches typos). This is
the v1 string matcher; pgvector is a later drop-in via the same `PatternMatcher` port.
"""
from __future__ import annotations

import difflib
from typing import List


def _tokens(key: str) -> set:
    return {t for t in key.split("-") if t}


def _score(a: str, b: str) -> float:
    """Higher = more similar. Mean of token-Jaccard and char-sequence ratio."""
    ta, tb = _tokens(a), _tokens(b)
    jaccard = len(ta & tb) / len(ta | tb) if (ta or tb) else 0.0
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return (jaccard + ratio) / 2.0


def suggest_keys(key: str, known: List[str], n: int = 3) -> List[str]:
    scored = sorted(known, key=lambda k: _score(key, k), reverse=True)
    return scored[:n]


def is_known(key: str, known: List[str]) -> bool:
    return key in known
