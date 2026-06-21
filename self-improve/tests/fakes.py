"""In-memory test doubles: FakeIssueGateway + deterministic clock/id factories.

The fake implements the IssueGateway port with a list of issues and a marker search, so
dedup and wrap-up idempotency are testable with zero network and no mocking library.
"""
from __future__ import annotations

from typing import List, Optional

from siloop.core.issues import IssuePayload
from siloop.core.ports import IssueRef


class FakeIssueGateway:
    def __init__(self, raise_on_search: bool = False) -> None:
        self.issues = []          # list of dicts: url, number, state, marker, comments
        self.labels = set()
        self.raise_on_search = raise_on_search
        self._n = 0

    def ensure_labels(self, repo: str, labels: List[str]) -> None:
        self.labels.update(labels)

    def open_issue_for(self, repo: str, pattern_key: str) -> Optional[IssueRef]:
        if self.raise_on_search:
            raise RuntimeError("simulated GitHub outage")
        marker = "<!-- self-improve:pattern={} -->".format(pattern_key)
        for it in self.issues:
            if it["marker"] == marker and it["state"] == "open":
                return IssueRef(url=it["url"], number=it["number"], state="open")
        return None

    def file_issue(self, repo: str, payload: IssuePayload) -> IssueRef:
        self._n += 1
        it = {
            "url": "https://github.com/{}/issues/{}".format(repo, self._n),
            "number": self._n,
            "state": "open",
            "marker": payload.marker,
            "comments": [],
        }
        self.issues.append(it)
        return IssueRef(url=it["url"], number=it["number"], state="open")

    def comment(self, ref: IssueRef, body: str) -> None:
        for it in self.issues:
            if it["number"] == ref.number:
                it["comments"].append(body)

    # test helper
    def close(self, number: int) -> None:
        for it in self.issues:
            if it["number"] == number:
                it["state"] = "closed"


def seq_ids(prefix: str = "e"):
    """Deterministic id factory: e1, e2, ..."""
    counter = {"n": 0}

    def factory() -> str:
        counter["n"] += 1
        return "{}{}".format(prefix, counter["n"])

    return factory


def seq_clock(start: int = 1):
    """Deterministic, monotonically increasing ISO-ish timestamps."""
    counter = {"n": start - 1}

    def clock() -> str:
        counter["n"] += 1
        return "2026-06-21T00:00:{:02d}+00:00".format(counter["n"])

    return clock
