"""
Deterministic Ecosystem Health Scoring Engine for skillpulse.
Implements prd.md > Ecosystem Health Scoring.
"""

from typing import Tuple, List
from skillpulse.models import ScanResult, SkillReport, MCPReport, DiagnosticIssue


class HealthScorer:
    """Calculates deterministic composite health score and letter grades."""

    @classmethod
    def calculate_score(cls, errors: int, warnings: int, info: int = 0) -> Tuple[int, str]:
        """
        Calculates health score (0-100) and letter grade:
        Score = max(0, 100 - (25 * errors) - (10 * warnings) - (2 * info))
        """
        penalty = (25 * errors) + (10 * warnings) + (2 * info)
        score = max(0, 100 - penalty)

        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        else:
            grade = "F"

        return score, grade

    @classmethod
    def grade_description(cls, grade: str, errors: int = 0) -> str:
        if grade == "A":
            return "Grade A (Excellent Health - CI Ready)"
        elif grade == "B":
            return "Grade B (Good Health - Minor Warnings)"
        elif grade == "C":
            return "Grade C (Needs Improvement - Review Warnings)"
        else:
            if errors > 0:
                return f"Grade F (Failing - {errors} Critical Error(s) Present)"
            return "Grade F (Failing - Cumulative Warnings Exceeded Threshold)"

    @classmethod
    def score_scan(
        cls,
        skills: List[SkillReport],
        mcp_report: MCPReport = None,
        workspace_path: str = ".",
        timestamp: str = ""
    ) -> ScanResult:
        """Computes score and constructs a composite ScanResult."""
        total_errors = sum(s.error_count for s in skills)
        total_warnings = sum(s.warning_count for s in skills)
        total_info = sum(sum(1 for i in s.issues if i.severity == "INFO") for s in skills)

        if mcp_report:
            total_errors += mcp_report.error_count
            total_warnings += mcp_report.warning_count
            total_info += sum(1 for i in mcp_report.issues if i.severity == "INFO")

        score, grade = cls.calculate_score(total_errors, total_warnings, total_info)

        return ScanResult(
            timestamp=timestamp,
            workspace_path=workspace_path,
            health_score=score,
            grade=grade,
            skills=skills,
            mcp_report=mcp_report
        )
