"""
Unit tests for skillpulse.linter.
"""

from pathlib import Path
import pytest
from skillpulse.linter import SkillLinter, SkillScanner, SimpleYAMLParser
from skillpulse.models import SkillReport


SAMPLE_VALID_SKILL = """---
name: code-reviewer
description: Automatically reviews pull requests and provides suggestions when invoked.
tools:
  - git_diff
  - post_comment
---

# Code Reviewer Skill

Use when a developer asks for code review on an open pull request.
It invokes `git_diff` to inspect changes and runs `post_comment` with findings.
"""

SAMPLE_NO_DELIMITER = """
# Missing Frontmatter
name: no-frontmatter
description: Invalid skill without frontmatter.
"""

SAMPLE_MISSING_NAME = """---
description: This skill has no name.
---
# Content
Use when needed.
"""

SAMPLE_MISSING_DESC = """---
name: missing-desc
---
# Content
Use when needed.
"""

SAMPLE_NO_TRIGGERS = """---
name: no-triggers
description: A skill that does some calculation.
---
# Content
Performs math.
"""


def test_valid_skill():
    report = SkillLinter.lint_text(SAMPLE_VALID_SKILL, "SKILL.md")
    assert report.is_valid is True
    assert report.name == "code-reviewer"
    assert "git_diff" in report.referenced_tools
    assert "post_comment" in report.referenced_tools
    assert report.error_count == 0


def test_missing_frontmatter_delimiter():
    report = SkillLinter.lint_text(SAMPLE_NO_DELIMITER, "SKILL.md")
    assert report.is_valid is False
    assert any(i.rule_id == "SKILL001" for i in report.issues)


def test_missing_name_attribute():
    report = SkillLinter.lint_text(SAMPLE_MISSING_NAME, "SKILL.md")
    assert report.is_valid is False
    assert any(i.rule_id == "SKILL002" and i.severity == "ERROR" for i in report.issues)


def test_missing_description_attribute():
    report = SkillLinter.lint_text(SAMPLE_MISSING_DESC, "SKILL.md")
    assert report.is_valid is False
    assert any(i.rule_id == "SKILL003" and i.severity == "ERROR" for i in report.issues)


def test_trigger_guidance_warning():
    report = SkillLinter.lint_text(SAMPLE_NO_TRIGGERS, "SKILL.md")
    # Valid syntax, but warning for triggers
    assert any(i.rule_id == "SKILL004" and i.severity == "WARNING" for i in report.issues)


def test_token_budget_estimation():
    short_report = SkillLinter.lint_text(SAMPLE_VALID_SKILL, "SKILL.md")
    assert short_report.token_count > 0
    assert not any(i.rule_id == "SKILL005" for i in short_report.issues)

    # Large text (> 2000 words ~ 2600 tokens)
    large_body = "word " * 2200
    large_skill = f"---\nname: large-skill\ndescription: Use when testing oversized prompt payloads.\n---\n{large_body}"
    large_report = SkillLinter.lint_text(large_skill, "SKILL.md")
    assert large_report.token_count > 2500
    assert any(i.rule_id == "SKILL005" and i.severity == "WARNING" for i in large_report.issues)


def test_yaml_parser_inline_lists():
    yaml_text = "name: test-skill\ntools: [search_db, send_alert]\ndescription: A simple test"
    data, issues = SimpleYAMLParser.parse(yaml_text)
    assert not issues
    assert data["name"] == "test-skill"
    assert data["tools"] == ["search_db", "send_alert"]


def test_scanner_finds_skills(tmp_path: Path):
    skill_dir = tmp_path / "skill_a"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(SAMPLE_VALID_SKILL, encoding="utf-8")

    nested = tmp_path / "sub" / "skill_b"
    nested.mkdir(parents=True)
    (nested / "SKILL.md").write_text(SAMPLE_VALID_SKILL, encoding="utf-8")

    found = SkillScanner.find_skills(tmp_path)
    assert len(found) == 2
