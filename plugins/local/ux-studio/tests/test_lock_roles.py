"""Seam S1: entries are handled by declared role, never by name (#80)."""


def test_lock_without_a_design_md_index_entry_syncs_and_builds_no_index(ws):
    up = ws.upstream("acme/widget")
    sha = up.commit({"s/SKILL.md": "v1\n"})
    ws.write_lock([("widget", "acme/widget", sha, "s", "skills/widget", "-", "skill")])

    result = ws.run("sync-vendor.sh", check=False)

    assert result.returncode == 0, result.stderr
    assert ws.read("skills/widget/SKILL.md") == "v1\n"
    assert not list(ws.root.glob("skills/**/INDEX.md"))


def test_index_is_built_from_the_entry_with_the_index_role_whatever_its_name(ws, design_upstream):
    _, sha = design_upstream
    (ws.root / "skills/refs").mkdir(parents=True)
    ws.write_lock([("refs", "acme/awesome-design-md", sha,
                    "README.md", "skills/refs/upstream-README.md", "-", "design-md-index")])

    result = ws.run("sync-vendor.sh")

    index = ws.read("skills/refs/INDEX.md")
    assert "| `linear` | Linear |" in index and "`slack`" in index
    assert "design-md index: 4 sites" in result.stdout
