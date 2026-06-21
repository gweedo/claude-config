"""pattern_key matcher: reject-unknown + 3-closest (DESIGN §11 T6, PROTOCOL §5)."""
from siloop.core.patterns import is_known, suggest_keys

KNOWN = ["infra-leak-in-app", "missing-type-hints", "raw-sql-in-router",
         "hardcoded-secret", "no-error-handling-external-api"]


def test_exact_key_is_known():
    assert is_known("raw-sql-in-router", KNOWN)
    assert not is_known("raw-sql-in-handler", KNOWN)


def test_suggest_surfaces_token_overlap_near_dup():
    # shares tokens raw/sql/in -> should rank raw-sql-in-router first
    suggestions = suggest_keys("sql-raw-in-handler", KNOWN, n=3)
    assert suggestions[0] == "raw-sql-in-router"
    assert len(suggestions) == 3


def test_suggest_catches_typo_via_edit_distance():
    assert "missing-type-hints" in suggest_keys("mising-type-hint", KNOWN, n=3)
