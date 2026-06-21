"""GithubGateway — the one place that talks to GitHub (DESIGN §3).

Implements `IssueGateway` with stdlib urllib so the tool stays dependency-free. The token
comes from the `GITHUB_TOKEN` env var only (PROTOCOL §9 / DESIGN §7). The loop-language
methods hide GitHub's REST shape from core: dedup is a label + exact-marker match, never
GitHub's fuzzy full-text ranking (DESIGN §6).

NOTE: this networked adapter still needs the contract test in DESIGN §11 (T8) before
production use; the pure core and use cases are what the test suite covers today.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import List, Optional

from ..core.issues import IssuePayload
from ..core.ports import IssueRef

_API = "https://api.github.com"


class GithubError(RuntimeError):
    pass


class GithubGateway:
    def __init__(self, token: Optional[str] = None) -> None:
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            raise GithubError("GITHUB_TOKEN not set")

    # --- HTTP helpers ---
    def _request(self, method: str, url: str, body: Optional[dict] = None) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", "Bearer " + self.token)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "siloop")
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            # 422 on label creation = already exists; let callers decide
            raise GithubError("{} {} -> {}".format(method, url, exc.code))
        except urllib.error.URLError as exc:
            raise GithubError("network error: {}".format(exc))

    # --- IssueGateway ---
    def ensure_labels(self, repo: str, labels: List[str]) -> None:
        for name in labels:
            try:
                self._request("POST", "{}/repos/{}/labels".format(_API, repo),
                              {"name": name})
            except GithubError:
                pass  # already exists (422) or insufficient perms — non-fatal

    def open_issue_for(self, repo: str, pattern_key: str) -> Optional[IssueRef]:
        marker = "<!-- self-improve:pattern={} -->".format(pattern_key)
        q = 'repo:{} label:self-improve state:open "{}"'.format(repo, marker)
        url = "{}/search/issues?q={}".format(_API, urllib.parse.quote(q))
        result = self._request("GET", url)  # raises on network failure (grill-me #1)
        for item in result.get("items", []):
            if marker in (item.get("body") or ""):   # exact-marker confirmation
                return IssueRef(url=item["html_url"], number=item["number"],
                                state=item.get("state", "open"),
                                state_reason=item.get("state_reason"))
        return None

    def file_issue(self, repo: str, payload: IssuePayload) -> IssueRef:
        result = self._request(
            "POST", "{}/repos/{}/issues".format(_API, repo),
            {"title": payload.title, "body": payload.body, "labels": payload.labels},
        )
        return IssueRef(url=result["html_url"], number=result["number"],
                        state=result.get("state", "open"))

    def comment(self, ref: IssueRef, body: str) -> None:
        self._request("POST",
                      "{}/repos/{}/issues/{}/comments".format(_API, _repo_from_url(ref.url), ref.number),
                      {"body": body})


def _repo_from_url(html_url: str) -> str:
    # https://github.com/owner/name/issues/42 -> owner/name
    parts = html_url.split("github.com/", 1)[-1].split("/")
    return "/".join(parts[:2])
