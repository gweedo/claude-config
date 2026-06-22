"""IssueGateway adapter contract (DESIGN §11 T8).

The one networked module. `urlopen` is stubbed so these stay offline in CI; they pin the
contract the dedup/idempotency guarantee depends on at runtime:
  * the dedup search is built with label:self-improve + state:open + the exact marker;
  * a marker match returns an IssueRef, a non-match returns None;
  * a network failure RAISES (never a silent empty -> "safe to create", grill-me #1);
  * create / comment / ensure-labels hit the right endpoints.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

import pytest

from siloop.adapters.github import GithubError, GithubGateway
from siloop.core.issues import build_issue
from siloop.core.models import FixType, Pattern, Status
from siloop.core.ports import IssueRef


class _Resp:
    def __init__(self, payload):
        self._b = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _install(monkeypatch, handler):
    calls = []

    def fake_urlopen(req, *a, **k):
        method = req.get_method()
        url = req.full_url
        body = json.loads(req.data.decode("utf-8")) if req.data else None
        calls.append((method, url, body))
        return handler(method, url, body)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return calls


def _gw():
    return GithubGateway(token="t0ken")


def test_open_issue_for_builds_query_and_matches_marker(monkeypatch):
    marker = "<!-- self-improve:pattern=infra-leak-in-app -->"

    def handler(method, url, body):
        assert method == "GET"
        assert "search/issues" in url
        decoded = urllib.parse.unquote(url)
        assert "label:self-improve" in decoded
        assert "state:open" in decoded
        assert marker in decoded
        return _Resp({"items": [
            {"html_url": "https://github.com/o/r/issues/7", "number": 7,
             "state": "open", "state_reason": None, "body": "intro\n" + marker + "\nrest"},
        ]})

    _install(monkeypatch, handler)
    ref = _gw().open_issue_for("o/r", "infra-leak-in-app")
    assert ref.number == 7
    assert ref.url.endswith("/issues/7")
    assert ref.state == "open"


def test_open_issue_for_returns_none_when_marker_absent(monkeypatch):
    # a substring/unrelated body must NOT false-match (exact marker required)
    def handler(method, url, body):
        return _Resp({"items": [
            {"html_url": "https://github.com/o/r/issues/1", "number": 1,
             "state": "open", "body": "talks about infra-leak but no marker"},
        ]})

    _install(monkeypatch, handler)
    assert _gw().open_issue_for("o/r", "infra-leak-in-app") is None


def test_open_issue_for_raises_on_network_failure(monkeypatch):
    # the load-bearing contract: a failed search must raise, never return None
    def handler(method, url, body):
        raise urllib.error.URLError("connection refused")

    _install(monkeypatch, handler)
    with pytest.raises(GithubError):
        _gw().open_issue_for("o/r", "k")


def test_file_issue_posts_and_returns_ref(monkeypatch):
    pattern = Pattern("infra-leak-in-app", 2, 2, Status.FIXABLE, "t1", "t2",
                      ["e1", "e2"], None, FixType.SCRIPT)
    payload = build_issue(pattern, title="RouteService queries DB",
                          root_cause="no rule", proposed_fix="add rule", session_id="s")

    def handler(method, url, body):
        assert method == "POST"
        assert url.endswith("/repos/o/r/issues")
        assert body["title"] == payload.title
        assert body["labels"] == ["self-improve", "fix:script"]
        assert payload.marker in body["body"]
        return _Resp({"html_url": "https://github.com/o/r/issues/9",
                      "number": 9, "state": "open"})

    _install(monkeypatch, handler)
    ref = _gw().file_issue("o/r", payload)
    assert ref.number == 9
    assert ref.url.endswith("/issues/9")


def test_ensure_labels_tolerates_existing_label(monkeypatch):
    def handler(method, url, body):
        raise urllib.error.HTTPError(url, 422, "already_exists", {}, None)

    _install(monkeypatch, handler)
    # must not raise: a 422 (label exists) is non-fatal
    _gw().ensure_labels("o/r", ["self-improve", "fix:script"])


def test_comment_posts_to_issue_comments_endpoint(monkeypatch):
    seen = {}

    def handler(method, url, body):
        seen.update(method=method, url=url, body=body)
        return _Resp({})

    _install(monkeypatch, handler)
    _gw().comment(IssueRef(url="https://github.com/o/r/issues/9", number=9, state="open"),
                  "recurred in session s")
    assert seen["method"] == "POST"
    assert seen["url"].endswith("/repos/o/r/issues/9/comments")
    assert seen["body"] == {"body": "recurred in session s"}
