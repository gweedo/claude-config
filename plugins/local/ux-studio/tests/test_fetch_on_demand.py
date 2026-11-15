"""Seam S2: fetch-on-demand.sh fetches an entry's on-demand folder at its pinned commit, once (#77, #80)."""
import subprocess

from conftest import PLUGIN

DEST = "skills/design-taste-frontend"


def _setup(ws):
    up = ws.upstream("acme/taste")
    sha = up.commit({"skills/taste/SKILL.md": "taste\n",
                     "skills/taste/assets/system.css": "v1\n",
                     "skills/taste/assets/old.svg": "<svg/>\n"})
    ws.write_lock([("design-taste-frontend", "acme/taste", sha, "skills/taste", DEST, "assets", "skill")])
    return up, sha


def test_first_run_fetches_assets_from_the_pinned_commit(ws):
    up, _ = _setup(ws)
    up.commit({"skills/taste/assets/system.css": "v2-unpinned\n"})

    ws.run("fetch-on-demand.sh", "design-taste-frontend")

    assert ws.read(f"{DEST}/assets/system.css") == "v1\n"


def test_second_run_at_the_same_pin_is_a_no_op(ws):
    _setup(ws)
    ws.run("fetch-on-demand.sh", "design-taste-frontend")
    (ws.root / f"{DEST}/assets/marker").write_text("keep\n")

    result = ws.run("fetch-on-demand.sh", "design-taste-frontend")

    assert "already at" in result.stdout
    assert ws.exists(f"{DEST}/assets/marker")


def test_moved_pin_replaces_assets_and_drops_stale_files(ws):
    up, _ = _setup(ws)
    ws.run("fetch-on-demand.sh", "design-taste-frontend")
    new = up.commit({"skills/taste/assets/system.css": "v2\n"},
                    delete=["skills/taste/assets/old.svg"])
    ws.write_lock([("design-taste-frontend", "acme/taste", new, "skills/taste", DEST, "assets", "skill")])

    ws.run("fetch-on-demand.sh", "design-taste-frontend")

    assert ws.read(f"{DEST}/assets/system.css") == "v2\n"
    assert not ws.exists(f"{DEST}/assets/old.svg")


def test_fetched_assets_are_git_ignored():
    """Checked against the real plugin's ignore rules, where the assets actually land."""
    result = subprocess.run(
        ["git", "check-ignore", "-q", f"{DEST}/assets/system.css"],
        cwd=PLUGIN, capture_output=True,
    )
    assert result.returncode == 0


def test_works_with_a_grep_that_lacks_perl_regex(ws, tmp_path):
    """BSD/macOS grep has no -P; simulate it with a shim that rejects -P."""
    import os, shutil
    shim = tmp_path / "bin"
    shim.mkdir()
    real = shutil.which("grep")
    (shim / "grep").write_text(
        f'#!/usr/bin/env bash\nfor a in "$@"; do [[ "$a" == -*P* && "$a" != --* ]] && '
        f'{{ echo "grep: invalid option -- P" >&2; exit 2; }}; done\nexec {real} "$@"\n')
    (shim / "grep").chmod(0o755)
    _setup(ws)
    env = {**os.environ, "UX_STUDIO_GIT_BASE": ws.base.as_uri(), "PATH": f"{shim}:{os.environ['PATH']}"}

    result = subprocess.run(["bash", str(ws.root / "scripts/fetch-on-demand.sh"), "design-taste-frontend"],
                            cwd=ws.root, env=env, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert ws.read(f"{DEST}/assets/system.css") == "v1\n"


def test_without_a_name_fetches_every_entry_with_an_on_demand_folder(ws):
    _setup(ws)
    other = ws.upstream("acme/other")
    osha = other.commit({"o/SKILL.md": "o\n", "o/media/clip.txt": "clip\n"})
    lock = (ws.root / "vendor.lock").read_text()
    (ws.root / "vendor.lock").write_text(
        lock + f"other\tacme/other\t{osha}\to\tskills/other\tmedia\tskill\n"
        + "plain\tacme/plain\tdeadbeef\tp\tskills/plain\t-\tskill\n")

    ws.run("fetch-on-demand.sh")

    assert ws.read(f"{DEST}/assets/system.css") == "v1\n"
    assert ws.read("skills/other/media/clip.txt") == "clip\n"
    assert not ws.exists("skills/plain")


def test_unknown_name_fails(ws):
    _setup(ws)

    result = ws.run("fetch-on-demand.sh", "tsate", check=False)

    assert result.returncode != 0 and "tsate" in result.stderr


def test_with_a_name_fetches_only_that_entry(ws):
    _setup(ws)
    other = ws.upstream("acme/other")
    osha = other.commit({"o/media/clip.txt": "clip\n"})
    lock = (ws.root / "vendor.lock").read_text()
    (ws.root / "vendor.lock").write_text(lock + f"other\tacme/other\t{osha}\to\tskills/other\tmedia\tskill\n")

    ws.run("fetch-on-demand.sh", "design-taste-frontend")

    assert ws.exists(f"{DEST}/assets/system.css")
    assert not ws.exists("skills/other")
