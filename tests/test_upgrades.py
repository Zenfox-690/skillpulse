"""
Unit and integration tests for SkillPulse Sprint Upgrades:
- ScanResult.from_dict deserialization & roundtrips
- CLI --format json & --format markdown outputs
- CLI --json-output independent file saving
- CLI report --from-json rehydration without filesystem re-scanning
- WorkspaceFixer deterministic auto-remediation (dry-run & output-dir)
- HTMLReporter topology map and context budget meter rendering
"""

import json
from pathlib import Path
import pytest

from skillpulse.cli import main
from skillpulse.fixer import WorkspaceFixer
from skillpulse.models import ScanResult, SkillReport, MCPReport, MCPTool, DiagnosticIssue
from skillpulse.reporter import HTMLReporter


def test_models_from_dict_roundtrip():
    original = ScanResult(
        timestamp="2026-10-24 22:00:00",
        workspace_path="/workspace/test",
        health_score=95,
        grade="A",
        skills=[
            SkillReport(
                file_path="/workspace/test/skills/skill-a/SKILL.md",
                name="skill-a",
                description="A test skill",
                is_valid=True,
                token_count=150,
                referenced_tools=["tool_one"],
                issues=[
                    DiagnosticIssue(
                        rule_id="SKILL004",
                        severity="WARNING",
                        message="Missing trigger",
                        line_number=5,
                        suggestion="Add trigger"
                    )
                ]
            )
        ],
        mcp_report=MCPReport(
            source_file="/workspace/test/mcp_tools.json",
            protocol_version="2025-11-25",
            tools=[
                MCPTool(
                    name="tool_one",
                    description="Tool description",
                    input_schema={"type": "object", "properties": {"arg": {"type": "string"}}, "required": ["arg"]}
                )
            ],
            ghost_tools=[],
            orphan_tools=[],
            issues=[]
        )
    )

    data = original.to_dict()
    rehydrated = ScanResult.from_dict(data)

    assert rehydrated.timestamp == original.timestamp
    assert rehydrated.workspace_path == original.workspace_path
    assert rehydrated.health_score == original.health_score
    assert rehydrated.grade == original.grade
    assert rehydrated.total_errors == 0
    assert rehydrated.total_warnings == 1
    assert len(rehydrated.skills) == 1
    assert rehydrated.skills[0].name == "skill-a"
    assert rehydrated.skills[0].issues[0].rule_id == "SKILL004"
    assert rehydrated.mcp_report is not None
    assert rehydrated.mcp_report.tools[0].name == "tool_one"


def test_diagnostic_issue_from_dict_defaults():
    minimal_data = {"message": "Something went wrong"}
    issue = DiagnosticIssue.from_dict(minimal_data)
    assert issue.rule_id == "UNKNOWN"
    assert issue.severity == "ERROR"
    assert issue.message == "Something went wrong"
    assert issue.line_number is None
    assert issue.suggestion == ""


def test_cli_format_json_scan(capsys):
    exit_code = main([
        "scan",
        "--skills-dir", "examples/healthy_workspace/skills",
        "--mcp-config", "examples/healthy_workspace/mcp_tools.json",
        "--format", "json"
    ])
    captured = capsys.readouterr()
    assert exit_code == 0

    # Ensure stdout is 100% valid JSON without banners
    data = json.loads(captured.out.strip())
    assert data["health_score"] == 100
    assert data["grade"] == "A"
    assert data["total_errors"] == 0
    assert len(data["skills"]) == 2
    assert data["mcp_report"] is not None
    assert len(data["mcp_report"]["tools"]) == 3


def test_cli_format_markdown_scan(capsys):
    exit_code = main([
        "scan",
        "--skills-dir", "examples/healthy_workspace/skills",
        "--mcp-config", "examples/healthy_workspace/mcp_tools.json",
        "--format", "markdown"
    ])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "## 🔍 SkillPulse Diagnostics & Health Summary" in captured.out
    assert "**Health Score:** `100%` (**Grade A**)" in captured.out
    assert "Agent Skills Scanned" in captured.out
    assert "MCP Tools Verified" in captured.out
    assert "All Agent Skills and MCP tool schemas passed validation cleanly" in captured.out


def test_cli_json_output_file(tmp_path: Path, capsys):
    json_target = tmp_path / "artifacts" / "scan_output.json"
    exit_code = main([
        "scan",
        "--skills-dir", "examples/healthy_workspace/skills",
        "--mcp-config", "examples/healthy_workspace/mcp_tools.json",
        "--json-output", str(json_target)
    ])
    assert exit_code == 0
    assert json_target.exists()

    saved_data = json.loads(json_target.read_text(encoding="utf-8"))
    assert saved_data["health_score"] == 100
    assert saved_data["grade"] == "A"


def test_cli_report_from_json(tmp_path: Path, capsys):
    # 1. Create a dummy scan json
    sample_result = {
        "timestamp": "2026-10-24 15:30:00",
        "workspace_path": "/ci/workspace",
        "health_score": 85,
        "grade": "B",
        "skills": [
            {
                "file_path": "skills/demo/SKILL.md",
                "name": "demo-skill",
                "description": "Demo skill description",
                "is_valid": True,
                "token_count": 210,
                "referenced_tools": ["mcp_demo_tool"],
                "issues": []
            }
        ],
        "mcp_report": {
            "source_file": "mcp_tools.json",
            "protocol_version": "2025-11-25",
            "tools": [
                {
                    "name": "mcp_demo_tool",
                    "description": "Demo tool",
                    "input_schema": {"type": "object", "properties": {}}
                }
            ],
            "ghost_tools": [],
            "orphan_tools": [],
            "issues": []
        }
    }
    json_path = tmp_path / "scan_export.json"
    json_path.write_text(json.dumps(sample_result), encoding="utf-8")

    html_out = tmp_path / "rehydrated_report.html"
    exit_code = main(["report", "--from-json", str(json_path), "--output", str(html_out)])
    assert exit_code == 0
    assert html_out.exists()

    content = html_out.read_text(encoding="utf-8")
    assert "85%" in content
    assert "Grade B" in content
    assert "demo-skill" in content
    assert "mcp_demo_tool" in content
    assert "Contract Topology Map" in content


def test_cli_report_from_json_missing(capsys):
    exit_code = main(["report", "--from-json", "non_existent_file_xyz.json"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "not found" in captured.out


def test_workspace_fixer_dry_run():
    # Dry run against broken workspace must not modify disk
    fixer = WorkspaceFixer(
        workspace_root=Path("examples/broken_workspace"),
        skills_dir=Path("examples/broken_workspace/skills"),
        mcp_config_path=Path("examples/broken_workspace/mcp_tools.json"),
        dry_run=True,
    )
    result = fixer.fix()

    assert result.dry_run is True
    assert result.total_actions > 0
    # Must propose MCP003 ghost tool stub and MCP002 schema repair
    rule_ids = [a.rule_id for a in result.actions]
    assert "MCP003" in rule_ids
    assert "MCP002" in rule_ids

    # Verify no actions were applied
    assert all(not a.applied for a in result.actions)

    # Ensure source broken file is unchanged
    broken_mcp = Path("examples/broken_workspace/mcp_tools.json").read_text(encoding="utf-8")
    assert "broken_schema_tool" in broken_mcp
    assert "delete_production_db" not in broken_mcp


def test_workspace_fixer_output_dir(tmp_path: Path):
    out_dir = tmp_path / "repaired_workspace"

    fixer = WorkspaceFixer(
        workspace_root=Path("examples/broken_workspace"),
        skills_dir=Path("examples/broken_workspace/skills"),
        mcp_config_path=Path("examples/broken_workspace/mcp_tools.json"),
        dry_run=False,
        output_dir=out_dir,
    )
    result = fixer.fix()

    assert result.dry_run is False
    assert result.total_actions > 0

    # Ensure files were cloned and repaired in out_dir
    repaired_mcp = out_dir / "mcp_tools.json"
    assert repaired_mcp.exists()

    data = json.loads(repaired_mcp.read_text(encoding="utf-8"))
    tool_names = [t["name"] for t in data["tools"]]

    # Ghost tool delete_production_db should now have an auto-generated stub
    assert "delete_production_db" in tool_names

    # Broken schema tool should now have valid object inputSchema
    for t in data["tools"]:
        if t["name"] == "broken_schema_tool":
            assert t.get("inputSchema") is not None
            assert t["inputSchema"]["type"] == "object"

    # Pre-scan was 25% (Grade F), post-scan should be 80% (Grade B) with 0 errors and 4 warnings (including MCP005 stub warning)
    assert result.pre_scan.health_score == 25
    assert result.pre_scan.grade == "F"
    assert result.post_scan.health_score == 80
    assert result.post_scan.grade == "B"
    assert result.post_scan.total_errors == 0
    assert result.post_scan.total_warnings == 4
    assert "delete_production_db" in result.post_scan.mcp_report.stub_tools


def test_cli_fix_subcommand(capsys):
    exit_code = main([
        "fix",
        "examples/broken_workspace",
        "--skills-dir", "examples/broken_workspace/skills",
        "--mcp-config", "examples/broken_workspace/mcp_tools.json",
        "--dry-run"
    ])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Workspace Fixer" in captured.out
    assert "DRY-RUN" in captured.out
    assert "MCP003" in captured.out
    assert "delete_production_db" in captured.out


def test_reporter_topology_and_budget_render(tmp_path: Path):
    scan_result = ScanResult(
        timestamp="2026-10-24 18:00:00",
        workspace_path="/test",
        health_score=85,
        grade="B",
        skills=[
            SkillReport(
                file_path="/test/SKILL.md",
                name="tester-skill",
                token_count=1200,
                referenced_tools=["sample_tool", "stub_tool"],
                issues=[]
            )
        ],
        mcp_report=MCPReport(
            source_file="/test/mcp.json",
            protocol_version="2025-11-25",
            tools=[
                MCPTool(name="sample_tool", input_schema={"type": "object", "properties": {}}, is_stub=False),
                MCPTool(name="stub_tool", description="[AUTO-GENERATED STUB] test", input_schema={"type": "object", "properties": {}}, is_stub=True)
            ],
            ghost_tools=[],
            orphan_tools=[],
            stub_tools=["stub_tool"],
            issues=[
                DiagnosticIssue(rule_id="MCP005", severity="WARNING", message="Unimplemented Stub")
            ]
        )
    )

    out_file = tmp_path / "dashboard.html"
    HTMLReporter.generate(scan_result, out_file)

    content = out_file.read_text(encoding="utf-8")
    assert "Contract Topology Map" in content
    assert "Model Context Budget Meter" in content
    assert "Copy PR Summary (Markdown)" in content
    assert "pr-markdown-payload" in content
    assert "tester-skill" in content
    assert "sample_tool" in content
    assert "stub_tool" in content
    assert "Schema Stub (Unimplemented)" in content
    assert "STUB / UNIMPLEMENTED" in content
    assert "Verified Contract" in content
