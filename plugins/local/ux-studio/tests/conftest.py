"""Fixtures: fake upstream git repos and a throwaway copy of the plugin to sync into.

Tests drive the plugin's scripts as commands (seams S1/S2 in spec #73) and point
them at local repos via UX_STUDIO_GIT_BASE, so nothing touches the network.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LOCK_HEADER = "# name\trepo\tsha\tsrc_path\tdest\ton_demand\trole\n"


def git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
        env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"},
    ).stdout.strip()


class Upstream:
    """A fake upstream repo at <base>/<owner>/<name>."""

    def __init__(self, base: Path, slug: str):
        self.slug = slug
        self.path = base / slug
        self.path.mkdir(parents=True)
        git(self.path, "init", "-q", "-b", "main")

    def commit(self, files: dict, delete=()) -> str:
        for rel in delete:
            target = self.path / rel
            shutil.rmtree(target) if target.is_dir() else target.unlink()
        for rel, content in files.items():
            f = self.path / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content)
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "-m", "c", "--allow-empty")
        return git(self.path, "rev-parse", "HEAD")


class Workspace:
    """A temp copy of the plugin's scripts plus a vendor.lock we control."""

    def __init__(self, root: Path, base: Path):
        self.root = root
        self.base = base
        shutil.copytree(PLUGIN / "scripts", root / "scripts")
        (root / "skills").mkdir()

    def upstream(self, slug: str) -> Upstream:
        return Upstream(self.base, slug)

    def write_lock(self, rows):
        """rows: (name, repo, sha, src, dest, on_demand[, role]); role defaults to skill,
        except the awesome-design-md fixture, which is the design-md-index."""
        def full(r):
            if len(r) == 7:
                return r
            return (*r, "design-md-index" if r[0] == "awesome-design-md" else "skill")
        lines = [LOCK_HEADER] + ["\t".join(full(r)) + "\n" for r in rows]
        (self.root / "vendor.lock").write_text("".join(lines))

    def lock(self) -> dict:
        rows = [l.split("\t") for l in (self.root / "vendor.lock").read_text().splitlines()
                if l and not l.startswith("#")]
        return {r[0]: r for r in rows}

    def run(self, script, *args, check=True):
        env = {**os.environ, "UX_STUDIO_GIT_BASE": self.base.as_uri()}
        return subprocess.run(
            ["bash", str(self.root / "scripts" / script), *args],
            cwd=self.root, env=env, check=check, capture_output=True, text=True,
        )

    def read(self, rel):
        return (self.root / rel).read_text()

    def exists(self, rel):
        return (self.root / rel).exists()


@pytest.fixture
def ws(tmp_path):
    return Workspace(tmp_path / "plugin", tmp_path / "upstreams")


DESIGN_README = """# Awesome DESIGN.md

## Collection

### Tools

- [**Linear**](https://getdesign.md/linear/design-md) - Issue tracker. Dark, precise
- [**Cal**](https://getdesign.md/cal/design-md) - Scheduling. Calm neutrals

### Retail

- [**Airbnb**](https://getdesign.md/airbnb/design-md) - Travel marketplace. Warm coral

## Contributing

nothing
"""


@pytest.fixture
def design_upstream(ws):
    """Fixture awesome-design-md: README lists 3 sites, repo has 4 (slack unlisted)."""
    up = ws.upstream("acme/awesome-design-md")
    files = {"README.md": DESIGN_README, "LICENSE": "MIT"}
    for slug in ("linear", "cal", "airbnb", "slack"):
        files[f"design-md/{slug}/DESIGN.md"] = f"# {slug}\n"
    sha = up.commit(files)
    (ws.root / "skills/design-md-reference").mkdir(parents=True)
    (ws.root / "skills/design-md-reference/SKILL.md").write_text("hand-written\n")
    return up, sha
