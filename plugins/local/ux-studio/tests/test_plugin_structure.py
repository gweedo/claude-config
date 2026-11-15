"""The real plugin stays loadable: manifest parses, every agent/skill has valid frontmatter (#78).

`claude plugin validate` (also run in CI) does not fail on a missing name or broken
frontmatter, so these checks cover that gap.
"""
import json

import pytest
import yaml

from conftest import PLUGIN

AGENTS = sorted((PLUGIN / "agents").glob("*.md"))
SKILLS = sorted((PLUGIN / "skills").glob("*/SKILL.md"))


def frontmatter(path):
    text = path.read_text()
    assert text.startswith("---\n"), f"{path.name}: must open with ---"
    head, sep, _ = text[4:].partition("\n---")
    assert sep, f"{path}: frontmatter never closes"
    data = yaml.safe_load(head)
    assert isinstance(data, dict), f"{path}: frontmatter is not a mapping"
    return data


def test_manifest_parses_and_names_the_plugin():
    manifest = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text())
    assert manifest["name"] == "ux-studio"


def test_expected_agents_and_skills_exist():
    assert {p.stem for p in AGENTS} == {"ux-ui-designer", "ux-reviewer"}
    assert {p.parent.name for p in SKILLS} >= {
        "ux-loop", "design-md-reference", "impeccable", "design-taste-frontend", "playwright-cli"}


@pytest.mark.parametrize("path", AGENTS + SKILLS, ids=lambda p: str(p.relative_to(PLUGIN)))
def test_frontmatter_has_name_and_description(path):
    data = frontmatter(path)
    assert isinstance(data.get("name"), str) and data["name"].strip()
    assert isinstance(data.get("description"), str) and data["description"].strip()


@pytest.mark.parametrize("path", AGENTS, ids=lambda p: p.stem)
def test_agent_name_matches_its_file(path):
    assert frontmatter(path)["name"] == path.stem


def test_reviewer_cannot_edit_files():
    tools = frontmatter(PLUGIN / "agents/ux-reviewer.md")["tools"]
    assert not {"Edit", "Write", "NotebookEdit"} & set(tools)


def test_every_finding_source_the_reviewer_emits_is_in_the_glossary():
    import re
    reviewer = (PLUGIN / "agents/ux-reviewer.md").read_text()
    sources = re.search(r"source: (.+)", reviewer).group(1).split(" | ")
    glossary = (PLUGIN / "CONTEXT.md").read_text().split("**Finding**:", 1)[1].split("\n**", 1)[0]
    words = {"impeccable-audit": "Impeccable audit", "impeccable-critique": "Impeccable critique",
             "taste-gate": "Taste gate", "playwright": "Playwright"}
    missing = [s for s in sources if words.get(s.strip(), s) not in glossary]
    assert not missing, f"glossary Finding entry lacks sources: {missing}"
