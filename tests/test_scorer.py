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
    # 100 - (1 * 20) = 80
    score, grade = HealthScorer.calculate_score(errors=1, warnings=0, info=0)
    assert score == 80
    assert grade == "B"


def test_single_warning_penalty():
    # 100 - (1 * 5) = 95
    score, grade = HealthScorer.calculate_score(errors=0, warnings=1, info=0)
    assert score == 95
    assert grade == "A"


def test_grade_d_boundary():
    # 100 - (1 * 20) - (3 * 5) = 65 -> Grade D (60-69)
    score, grade = HealthScorer.calculate_score(errors=1, warnings=3, info=0)
    assert score == 65
    assert grade == "D"


def test_combined_penalties():
    # 100 - (2 * 20) - (3 * 5) = 100 - 40 - 15 = 45 -> Grade F (<60)
    score, grade = HealthScorer.calculate_score(errors=2, warnings=3, info=2)
    assert score == 45
    assert grade == "F"


def test_floor_at_zero():
    score, grade = HealthScorer.calculate_score(errors=10, warnings=10, info=10)
    assert score == 0
    assert grade == "F"


def test_format_formula():
    formula = HealthScorer.format_formula(errors=1, warnings=2, score=70, grade="C")
    assert formula == "100 - (1 errors × 20) - (2 warnings × 5) = 70% (C)"


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
        issues=[DiagnosticIssue(rule_id="MCP004", severity="WARNING", message="orphan")]
    )

    scan_result = HealthScorer.score_scan(skills, mcp_report, workspace_path=".", timestamp="2026-10-20")
    # 100 - (0 * 20) - (2 * 5) = 90 (Grade A)
    assert scan_result.total_errors == 0
    assert scan_result.total_warnings == 2
    assert scan_result.health_score == 90
    assert scan_result.grade == "A"
