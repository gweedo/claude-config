"""The seams the use cases depend on but never construct (DESIGN §2).

* `IssueGateway` — the one network seam. `adapters/github.py` is the real adapter;
  `tests/fakes.py` provides an in-memory one. The port speaks the loop's language
  (`open_issue_for(pattern_key)`), not GitHub's, so dedup/marker syntax stays inside the
  adapter.
* `PatternMatcher` — pattern_key similarity, so pgvector can later replace string
  distance without touching core.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

try:
    from typing import Protocol
except ImportError:  # pragma: no cover - Python < 3.8
    from typing_extensions import Protocol  # type: ignore

from .issues import IssuePayload


@dataclass
class IssueRef:
    url: str
    number: int
    state: str            # "open" | "closed"
    state_reason: Optional[str] = None   # "completed" | "not_planned" | None


class IssueGateway(Protocol):
    def ensure_labels(self, repo: str, labels: List[str]) -> None: ...

    def open_issue_for(self, repo: str, pattern_key: str) -> Optional[IssueRef]:
        """Live search: an OPEN issue carrying the pattern marker, or None.

        Must distinguish 'searched, found none' (return None) from 'could not search'
        (raise) so wrap_up never reads a failed search as 'safe to create' (grill-me #1).
        """

    def file_issue(self, repo: str, payload: IssuePayload) -> IssueRef: ...

    def comment(self, ref: IssueRef, body: str) -> None: ...


class PatternMatcher(Protocol):
    def is_known(self, key: str, known: List[str]) -> bool: ...

    def suggest(self, key: str, known: List[str], n: int = 3) -> List[str]: ...
