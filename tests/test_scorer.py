"""
Unit tests for skillpulse.scorer.
"""

from skillpulse.scorer import HealthScorer
from skillpulse.models import SkillReport, MCPReport, DiagnosticIssue


def test_perfect_score():
    score, grade = HealthScorer.calculate_score(errors=0, warnings=0, info=0)
    assert score == 100
    assert grade == "A"


def test_single_error_penalty():
    # 100 - (1 * 25) = 75
    score, grade = HealthScorer.calculate_score(errors=1, warnings=0, info=0)
    assert score == 75
    assert grade == "C"


def test_warning_penalty():
    # 100 - (1 * 10) = 90
    score, grade = HealthScorer.calculate_score(errors=0, warnings=1, info=0)
    assert score == 90
    assert grade == "A"


def test_combined_penalties():
    # 100 - (1 * 25) - (2 * 10) - (2 * 2) = 100 - 25 - 20 - 4 = 51
    score, grade = HealthScorer.calculate_score(errors=1, warnings=2, info=2)
    assert score == 51
    assert grade == "F"


def test_floor_at_zero():
    score, grade = HealthScorer.calculate_score(errors=10, warnings=10, info=10)
    assert score == 0
    assert grade == "F"


def test_score_scan_integration():
    skills = [
        SkillReport(
            file_path="skill_a.md",
            name="skill-a",
            is_valid=True,
            issues=[DiagnosticIssue(rule_id="SKILL004", severity="WARNING", message="warn")]
        )
    ]
    mcp_report = MCPReport(
        source_file="mcp.json",
        issues=[DiagnosticIssue(rule_id="MCP004", severity="INFO", message="info")]
    )

    scan_result = HealthScorer.score_scan(skills, mcp_report, workspace_path=".", timestamp="2026-10-20")
    # 100 - (1 * 10) - (1 * 2) = 88
    assert scan_result.health_score == 88
    assert scan_result.grade == "B"
    assert scan_result.total_errors == 0
    assert scan_result.total_warnings == 1
