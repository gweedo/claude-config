"""Seam S1: scripts/sync-vendor.sh re-vendors exactly what vendor.lock pins (#74)."""


def skill_row(name, slug, sha, src, dest, exclude="-"):
    return (name, slug, sha, src, dest, exclude)


def test_vendors_files_from_the_pinned_commit_not_head(ws, design_upstream):
    up_design, design_sha = design_upstream
    up = ws.upstream("acme/widget")
    pinned = up.commit({"skills/widget/SKILL.md": "v1\n", "LICENSE": "Apache"})
    up.commit({"skills/widget/SKILL.md": "v2\n"})  # HEAD moves past the pin
    ws.write_lock([
        skill_row("widget", "acme/widget", pinned, "skills/widget", "skills/widget"),
        skill_row("awesome-design-md", "acme/awesome-design-md", design_sha,
                  "README.md", "skills/design-md-reference/upstream-README.md"),
    ])

    ws.run("sync-vendor.sh")

    assert ws.read("skills/widget/SKILL.md") == "v1\n"


def _two_skills(ws, design_upstream):
    """widget (with an excluded assets/ folder) + the design-md README entry."""
    _, design_sha = design_upstream
    up = ws.upstream("acme/widget")
    sha = up.commit({
        "skills/widget/SKILL.md": "v1\n",
        "skills/widget/assets/big.bin": "x" * 100,
        "skills/widget/refs/a.md": "ref\n",
        "LICENSE": "Apache-2.0\n",
        "NOTICE.md": "notice\n",
        "unrelated/file.txt": "not vendored\n",
    })
    ws.write_lock([
        ("widget", "acme/widget", sha, "skills/widget", "skills/widget", "assets"),
        ("awesome-design-md", "acme/awesome-design-md", design_sha,
         "README.md", "skills/design-md-reference/upstream-README.md", "-"),
    ])
    return sha, design_sha


def test_excluded_subfolder_is_left_out_of_the_vendored_copy(ws, design_upstream):
    _two_skills(ws, design_upstream)

    ws.run("sync-vendor.sh")

    assert ws.exists("skills/widget/refs/a.md")
    assert not ws.exists("skills/widget/assets")


def test_upstream_licence_and_notice_travel_with_the_vendored_folder(ws, design_upstream):
    _two_skills(ws, design_upstream)

    ws.run("sync-vendor.sh")

    assert ws.read("skills/widget/LICENSE") == "Apache-2.0\n"
    assert ws.read("skills/widget/NOTICE.md") == "notice\n"
    assert not ws.exists("skills/widget/file.txt")


def test_single_file_entry_lands_beside_hand_written_files(ws, design_upstream):
    _two_skills(ws, design_upstream)

    ws.run("sync-vendor.sh")

    assert ws.read("skills/design-md-reference/upstream-README.md").startswith("# Awesome DESIGN.md")
    assert ws.read("skills/design-md-reference/SKILL.md") == "hand-written\n"
    assert ws.read("skills/design-md-reference/UPSTREAM-LICENSE") == "MIT"


def test_stale_files_from_a_previous_sync_are_removed(ws, design_upstream):
    _two_skills(ws, design_upstream)
    (ws.root / "skills/widget").mkdir(parents=True, exist_ok=True)
    (ws.root / "skills/widget/stale.md").write_text("old\n")

    ws.run("sync-vendor.sh")

    assert not ws.exists("skills/widget/stale.md")


def test_vendor_record_lists_every_pin_with_its_commit(ws, design_upstream):
    sha, design_sha = _two_skills(ws, design_upstream)

    ws.run("sync-vendor.sh")

    record = ws.read("VENDOR.md")
    assert f"[`{sha[:12]}`](" in record and "| widget |" in record
    assert f"[`{design_sha[:12]}`](" in record and "| awesome-design-md |" in record
    assert "`assets/`" in record
