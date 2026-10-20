"""
Unit tests for skillpulse.reporter.
"""

from pathlib import Path
from skillpulse.reporter import HTMLReporter
from skillpulse.models import ScanResult, SkillReport, MCPReport, MCPTool, DiagnosticIssue


def test_generate_html_creates_valid_file(tmp_path: Path):
    scan_result = ScanResult(
        timestamp="2026-10-20 23:30:00",
        workspace_path="/workspace",
        health_score=94,
        grade="A",
        skills=[
            SkillReport(
                file_path="skills/weather/SKILL.md",
                name="weather-reporter",
                description="Fetches weather",
                token_count=120,
                referenced_tools=["get_weather"],
                issues=[DiagnosticIssue(rule_id="SKILL004", severity="WARNING", message="Missing triggers", suggestion="Add trigger words")]
            )
        ],
        mcp_report=MCPReport(
            source_file="mcp_tools.json",
            protocol_version="2025-11-25",
            tools=[
                MCPTool(
                    name="get_weather",
                    description="Gets weather by location",
                    input_schema={"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}
                )
            ]
        )
    )

    out_file = tmp_path / "report.html"
    result_path = HTMLReporter.generate(scan_result, out_file)

    assert result_path.exists()
    content = result_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "94%" in content
    assert "Grade A" in content
    assert "weather-reporter" in content
    assert "get_weather" in content
    assert "MCP 2025-11-25" in content
