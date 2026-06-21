"""build_issue(pattern, ...) -> IssuePayload, plus a mechanical pre-publish secret scrub.

Pure: no network. The hidden marker comment is the dedup anchor matched by exact string
equality in the GitHub adapter (DESIGN §6). `scrub` is defense-in-depth behind PROTOCOL
§9's human rule — it refuses to build an issue whose body trips a secret denylist, so a
slip never reaches a public issue.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from .models import FIX_LABELS, FixType, Pattern

MARKER = "<!-- self-improve:pattern={key} -->"

# recap files always live in claude-config, so cross-repo (--issue-repo) issues still link
RECAP_BASE = "https://github.com/gweedo/claude-config/blob/main/self-improve/sessions"

_SECRET_PATTERNS = [
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),          # GitHub tokens
    re.compile(r"AKIA[0-9A-Z]{16}"),                     # AWS access key id
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),   # private keys
    re.compile(r"(?i)password\s*[=:]\s*\S+"),            # password=...
    re.compile(r"\b[A-Fa-f0-9]{40,}\b"),                 # long hex blobs (tokens/hashes)
]


class SecretLeak(ValueError):
    """Raised when an issue body trips the secret denylist."""


@dataclass
class IssuePayload:
    title: str
    body: str
    labels: List[str]
    marker: str


def scrub(text: str) -> None:
    for pat in _SECRET_PATTERNS:
        m = pat.search(text)
        if m:
            raise SecretLeak(
                "refusing to file: issue body matches secret pattern {!r}".format(pat.pattern)
            )


def build_issue(
    pattern: Pattern,
    title: str,
    root_cause: str,
    proposed_fix: str,
    session_id: str,
    affected_paths: Optional[List[str]] = None,
) -> IssuePayload:
    fix_type = pattern.fix_type or FixType.INSTRUCTION_UPDATE
    fix_label = FIX_LABELS[fix_type]
    marker = MARKER.format(key=pattern.pattern_key)
    paths = affected_paths or []

    body = "\n".join(
        [
            marker,
            "",
            "### Pattern",
            "`{}` - seen {}x (severity {})".format(
                pattern.pattern_key, pattern.count, pattern.max_severity
            ),
            "",
            "### Root cause",
            root_cause,
            "",
            "### Proposed fix ({})".format(fix_type.value),
            proposed_fix,
            "",
            "### Affected files",
        ]
        + (["- {}".format(p) for p in paths] or ["- (none recorded)"])
        + [
            "",
            "### Acceptance criteria",
            "- [ ] {}".format(proposed_fix),
            "- [ ] No regression of the pattern in a follow-up session",
            "",
            "### Provenance",
            "- First seen: {} - Last seen: {}".format(pattern.first_seen, pattern.last_seen),
            "- Source recap: {}/{}.md".format(RECAP_BASE, session_id),
            "- Event ids: {}".format(", ".join(pattern.event_ids)),
            "",
            "_Labels: `self-improve`, `{}`_".format(fix_label),
        ]
    )

    full_title = "[{}] {}".format(fix_label, title)
    scrub(full_title + "\n" + body)
    return IssuePayload(
        title=full_title,
        body=body,
        labels=["self-improve", fix_label],
        marker=marker,
    )
