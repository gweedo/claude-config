"""Seam S1: sync-vendor.sh --update bumps all or only the named pins (#75)."""


def _setup(ws, design_upstream):
    _, design_sha = design_upstream
    a, b = ws.upstream("acme/alpha"), ws.upstream("acme/beta")
    a1 = a.commit({"s/SKILL.md": "alpha v1\n"})
    b1 = b.commit({"s/SKILL.md": "beta v1\n"})
    ws.write_lock([
        ("alpha", "acme/alpha", a1, "s", "skills/alpha", "-"),
        ("beta", "acme/beta", b1, "s", "skills/beta", "-"),
        ("awesome-design-md", "acme/awesome-design-md", design_sha,
         "README.md", "skills/design-md-reference/upstream-README.md", "-"),
    ])
    a2 = a.commit({"s/SKILL.md": "alpha v2\n"})
    b2 = b.commit({"s/SKILL.md": "beta v2\n"})
    return (a1, a2), (b1, b2)


def test_update_without_names_moves_every_pin_to_head(ws, design_upstream):
    (_, a2), (_, b2) = _setup(ws, design_upstream)

    ws.run("sync-vendor.sh", "--update")

    assert ws.lock()["alpha"][2] == a2 and ws.lock()["beta"][2] == b2
    assert ws.read("skills/alpha/SKILL.md") == "alpha v2\n"
    assert ws.read("skills/beta/SKILL.md") == "beta v2\n"


def test_update_with_a_name_moves_only_that_pin(ws, design_upstream):
    (_, a2), (b1, _) = _setup(ws, design_upstream)

    ws.run("sync-vendor.sh", "--update", "alpha")

    assert ws.lock()["alpha"][2] == a2
    assert ws.lock()["beta"][2] == b1
    assert ws.read("skills/beta/SKILL.md") == "beta v1\n"


def test_vendor_record_shows_the_bumped_commit(ws, design_upstream):
    (a1, a2), _ = _setup(ws, design_upstream)

    ws.run("sync-vendor.sh", "--update", "alpha")

    record = ws.read("VENDOR.md")
    assert a2[:12] in record and a1[:12] not in record


def test_lock_header_survives_a_bump(ws, design_upstream):
    _setup(ws, design_upstream)

    ws.run("sync-vendor.sh", "--update")

    assert ws.read("vendor.lock").startswith("# name\trepo\tsha")
