"""build_issue marker + labels + secret scrub (DESIGN §11 T7, §6 / PROTOCOL §9)."""
import pytest

from siloop.core.issues import SecretLeak, build_issue
from siloop.core.models import FixType, Pattern, Status


def _pattern(fix_type=FixType.INSTRUCTION_UPDATE):
    return Pattern(pattern_key="infra-leak-in-app", count=2, max_severity=2,
                   status=Status.FIXABLE, first_seen="t1", last_seen="t2",
                   event_ids=["e1", "e2"], issue_url=None, fix_type=fix_type)


def test_marker_and_label_mapping():
    payload = build_issue(_pattern(FixType.SCRIPT), title="X queries DB",
                          root_cause="no rule", proposed_fix="add rule",
                          session_id="2026-06-21-ski", affected_paths=["a.py"])
    assert "<!-- self-improve:pattern=infra-leak-in-app -->" in payload.body
    assert payload.marker == "<!-- self-improve:pattern=infra-leak-in-app -->"
    assert payload.labels == ["self-improve", "fix:script"]
    assert payload.title.startswith("[fix:script]")


def test_secret_scrub_refuses_to_file():
    with pytest.raises(SecretLeak):
        build_issue(_pattern(), title="leak",
                    root_cause="token is ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                    proposed_fix="rotate", session_id="s")
