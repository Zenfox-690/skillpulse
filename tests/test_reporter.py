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


def test_copy_snippet_escaping_and_base64_remediation(tmp_path: Path):
    import base64
    import re

    complex_skill_suggestion = "Add 'description: Clear, action-oriented purpose' to frontmatter."
    complex_mcp_suggestion = 'Add \'inputSchema: {"type": "object", "properties": {"target": {"type": "string"}}}\' adhering to MCP 2025-11-25.'
    unicode_multiline_suggestion = "Fix line 1: use 'path\\to\\file'\nFix line 2: verify ✓ emoji & \"quotes\"."

    scan_result = ScanResult(
        timestamp="2026-10-25 00:00:00",
        workspace_path="/test_complex",
        health_score=60,
        grade="D",
        skills=[
            SkillReport(
                file_path="skills/complex/SKILL.md",
                name="complex-skill",
                token_count=350,
                referenced_tools=["complex_tool"],
                issues=[
                    DiagnosticIssue(
                        rule_id="SKILL003",
                        severity="ERROR",
                        message="Missing description",
                        suggestion=complex_skill_suggestion
                    ),
                    DiagnosticIssue(
                        rule_id="SKILL004",
                        severity="WARNING",
                        message="Trigger warnings",
                        suggestion=unicode_multiline_suggestion
                    )
                ]
            )
        ],
        mcp_report=MCPReport(
            source_file="mcp_tools.json",
            protocol_version="2025-11-25",
            tools=[
                MCPTool(name="complex_tool", input_schema={})
            ],
            issues=[
                DiagnosticIssue(
                    rule_id="MCP002",
                    severity="ERROR",
                    message="Broken schema",
                    suggestion=complex_mcp_suggestion
                )
            ]
        )
    )

    out_file = tmp_path / "complex_report.html"
    HTMLReporter.generate(scan_result, out_file)
    content = out_file.read_text(encoding="utf-8")

    # 1. Verify every Copy Fix button uses clean onclick="copySnippet(this)" without string parameters
    copy_fix_buttons = re.findall(r'<button class="btn btn-copy"[^>]*>Copy Fix</button>', content)
    assert len(copy_fix_buttons) == 3

    for btn_tag in copy_fix_buttons:
        assert 'onclick="copySnippet(this)"' in btn_tag
        assert "onclick=\"copySnippet(this, '" not in btn_tag

        # 2. Verify data-fix-b64 attribute exists and decodes correctly
        b64_match = re.search(r'data-fix-b64="([A-Za-z0-9+/=]+)"', btn_tag)
        assert b64_match is not None
        decoded_text = base64.b64decode(b64_match.group(1)).decode("utf-8")
        assert decoded_text in [complex_skill_suggestion, complex_mcp_suggestion, unicode_multiline_suggestion]

    # 3. Verify sibling <template class="fix-raw"> elements are present
    assert '<template class="fix-raw">' in content

    # 4. Verify script contains required helpers
    assert "function decodeBase64Utf8" in content
    assert "function copySnippet" in content
    assert "function copyToClipboard" in content
    assert "function fallbackCopy" in content
    assert "function copyPRSummary" in content
    assert "function showToast" in content

