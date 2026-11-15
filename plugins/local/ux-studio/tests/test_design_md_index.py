"""Seam S1: the Reference-design index is rebuilt accurately on every sync (#76)."""
import re


def _sync(ws, design_upstream):
    _, sha = design_upstream
    ws.write_lock([("awesome-design-md", "acme/awesome-design-md", sha,
                    "README.md", "skills/design-md-reference/upstream-README.md", "-")])
    result = ws.run("sync-vendor.sh")
    return sha, ws.read("skills/design-md-reference/INDEX.md"), result.stdout


def _section(index, heading):
    return index.split(f"### {heading}", 1)[1].split("\n### ", 1)[0]


def test_readme_entries_appear_under_their_category(ws, design_upstream):
    _, index, _ = _sync(ws, design_upstream)

    assert "| `linear` | Linear | Issue tracker. Dark, precise |" in _section(index, "Tools")
    assert "| `cal` | Cal | Scheduling. Calm neutrals |" in _section(index, "Tools")
    assert "| `airbnb` | Airbnb | Travel marketplace. Warm coral |" in _section(index, "Retail")


def test_sites_missing_from_the_readme_land_under_uncategorised(ws, design_upstream):
    _, index, _ = _sync(ws, design_upstream)

    uncategorised = _section(index, "Uncategorised")
    assert "`slack`" in uncategorised
    assert "`linear`" not in uncategorised


def test_reported_count_equals_upstream_folders(ws, design_upstream):
    _, _, stdout = _sync(ws, design_upstream)

    assert "design-md index: 4 sites" in stdout


def test_fetch_url_is_pinned_to_the_vendored_commit(ws, design_upstream):
    sha, index, _ = _sync(ws, design_upstream)

    assert f"https://raw.githubusercontent.com/acme/awesome-design-md/{sha}/design-md/<slug>/DESIGN.md" in index
    assert re.search(r"/main/|/HEAD/", index) is None
