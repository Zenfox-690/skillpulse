"""
Deterministic Ecosystem Health Scoring Engine for skillpulse.
Implements prd.md > Ecosystem Health Scoring.
"""

from typing import Tuple, List, Optional
from skillpulse.models import ScanResult, SkillReport, MCPReport


class HealthScorer:
    """Calculates deterministic composite health score and letter grades."""

    ERROR_PENALTY = 20
    WARNING_PENALTY = 5

    @classmethod
    def calculate_score(cls, errors: int, warnings: int, info: int = 0) -> Tuple[int, str]:
        """
        Calculates health score (0-100) and letter grade:
        Score = max(0, 100 - (20 * errors) - (5 * warnings))
        Grades: A (90-100), B (80-89), C (70-79), D (60-69), F (<60).
        """
        penalty = (cls.ERROR_PENALTY * errors) + (cls.WARNING_PENALTY * warnings)
        score = max(0, 100 - penalty)

        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"

        return score, grade

    @classmethod
    def grade_description(cls, grade: str, errors: int = 0) -> str:
        descriptions = {
            "A": "Grade A (Excellent Health - CI Ready)",
            "B": "Grade B (Good Health - Minor Warnings)",
            "C": "Grade C (Needs Improvement - Review Warnings)",
            "D": "Grade D (Marginal - Moderate Issues Detected)",
            "F": f"Grade F (Failing - {errors} Critical Error(s) Present)" if errors > 0 else "Grade F (Failing - Excessive Warnings)",
        }
        return descriptions.get(grade, f"Grade {grade}")

    @classmethod
    def format_formula(cls, errors: int, warnings: int, score: int, grade: str) -> str:
        """Returns human-readable score formula breakdown."""
        return (
            f"100 - ({errors} errors \u00d7 {cls.ERROR_PENALTY}) - "
            f"({warnings} warnings \u00d7 {cls.WARNING_PENALTY}) = {score}% ({grade})"
        )

    @classmethod
    def score_scan(
        cls,
        skills: List[SkillReport],
        mcp_report: Optional[MCPReport] = None,
        workspace_path: str = ".",
        timestamp: str = ""
    ) -> ScanResult:
        """Computes score and constructs a composite ScanResult."""
        total_errors = sum(s.error_count for s in skills)
        total_warnings = sum(s.warning_count for s in skills)

        if mcp_report:
            total_errors += mcp_report.error_count
            total_warnings += mcp_report.warning_count

        score, grade = cls.calculate_score(total_errors, total_warnings)

        return ScanResult(
            timestamp=timestamp,
            workspace_path=workspace_path,
            health_score=score,
            grade=grade,
            skills=skills,
            mcp_report=mcp_report
        )
