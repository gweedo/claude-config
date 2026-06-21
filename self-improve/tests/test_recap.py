"""recap renders a fixed SessionView and re-derives nothing (DESIGN §11 T5)."""
from siloop.core.models import SignalType, Verdict
from siloop.core.recap import IssueLine, LoggedLine, SessionView, WatchLine, build_recap


def test_render_sections_and_badges():
    view = SessionView(
        session_id="2026-06-20-ski",
        logged=[
            LoggedLine(SignalType.WRONG_APPROACH, "infra-leak-in-app", 2, Verdict.FIXABLE, 2),
            LoggedLine(SignalType.CODE_FAILURE, "aineva-missing-field", 2, Verdict.CASUAL, 1),
        ],
        promoted=[IssueLine("infra-leak-in-app", "fix:instructions", "Enforce repos",
                            "http://x/42")],
        watching=[WatchLine("aineva-missing-field", 1)],
    )
    md = build_recap(view)
    assert "## Logged this session (2)" in md
    assert "**fixable (2x)**" in md
    assert "casual (1x)" in md
    assert "[fix:instructions] Enforce repos" in md
    assert "`aineva-missing-field` (1x)" in md


def test_renderer_does_not_re_derive_counts():
    # feed a deliberately "wrong" count; recap must echo it verbatim, proving no rule lives here
    view = SessionView(
        session_id="s",
        logged=[LoggedLine(SignalType.CODE_FAILURE, "k", 1, Verdict.FIXABLE, 999)],
    )
    assert "fixable (999x)" in build_recap(view)
