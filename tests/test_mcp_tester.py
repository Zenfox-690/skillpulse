"""
Unit tests for skillpulse.mcp_tester.
"""

import json
from pathlib import Path
import pytest
from skillpulse.mcp_tester import MCPContractValidator, MCPConfigDiscovery
from skillpulse.models import SkillReport, DiagnosticIssue


SAMPLE_VALID_MCP = {
    "tools": [
        {
            "name": "lookup_user",
            "description": "Fetch user details by ID.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"}
                },
                "required": ["user_id"]
            }
        },
        {
            "name": "send_email",
            "description": "Send an outbound email notification.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "recipient": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["recipient", "body"]
            }
        }
    ]
}

SAMPLE_INVALID_SCHEMA = {
    "tools": [
        {
            "name": "broken_tool",
            "description": "Tool with invalid schema format",
            "inputSchema": "not-an-object"
        },
        {
            "description": "Tool missing name",
            "inputSchema": {"type": "object", "properties": {}}
        }
    ]
}


def test_valid_mcp_tools():
    report = MCPContractValidator.validate_tools_data(SAMPLE_VALID_MCP, "test.json")
    assert report.error_count == 0
    assert len(report.tools) == 2
    assert report.tools[0].name == "lookup_user"
    assert report.protocol_version == "2025-11-25"


def test_invalid_mcp_format():
    report = MCPContractValidator.validate_tools_data("not-valid-json-structure", "test.json")
    assert report.error_count > 0
    assert any(i.rule_id == "MCP001" for i in report.issues)


def test_missing_fields_and_schema_types():
    report = MCPContractValidator.validate_tools_data(SAMPLE_INVALID_SCHEMA, "test.json")
    assert report.error_count >= 2
    assert any(i.rule_id == "MCP002" and "inputSchema" in i.message for i in report.issues)
    assert any(i.rule_id == "MCP002" and "missing a required 'name'" in i.message for i in report.issues)


def test_ghost_tool_cross_checking():
    # Skill references 'execute_remote_query' which does not exist in SAMPLE_VALID_MCP
    mock_skill = SkillReport(
        file_path="skills/sql-agent/SKILL.md",
        name="sql-agent",
        referenced_tools=["execute_remote_query", "lookup_user"]
    )

    report = MCPContractValidator.validate_tools_data(
        SAMPLE_VALID_MCP,
        "test.json",
        scanned_skills=[mock_skill]
    )

    assert "execute_remote_query" in report.ghost_tools
    assert any(i.rule_id == "MCP003" and "Ghost Tool" in i.message for i in report.issues)


def test_orphan_tool_detection():
    # Skill only references 'lookup_user'. 'send_email' should be detected as orphan
    mock_skill = SkillReport(
        file_path="skills/user-agent/SKILL.md",
        name="user-agent",
        referenced_tools=["lookup_user"]
    )

    report = MCPContractValidator.validate_tools_data(
        SAMPLE_VALID_MCP,
        "test.json",
        scanned_skills=[mock_skill]
    )

    assert "send_email" in report.orphan_tools
    assert any(i.rule_id == "MCP004" and "send_email" in i.message for i in report.issues)


def test_malformed_json_file(tmp_path: Path):
    bad_file = tmp_path / "bad_mcp.json"
    bad_file.write_text("{ unquoted_key: 123 ", encoding="utf-8")

    report = MCPContractValidator.validate_file(bad_file)
    assert report.error_count > 0
    assert any(i.rule_id == "MCP001" and "Malformed JSON" in i.message for i in report.issues)


def test_config_discovery(tmp_path: Path):
    assert MCPConfigDiscovery.find_mcp_config(tmp_path) is None

    config_file = tmp_path / "mcp_tools.json"
    config_file.write_text(json.dumps(SAMPLE_VALID_MCP), encoding="utf-8")

    found = MCPConfigDiscovery.find_mcp_config(tmp_path)
    assert found == config_file


def test_unimplemented_stub_detection():
    data = {
        "tools": [
            {
                "name": "live_tool",
                "description": "Production ready tool",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "auto_stub_by_field",
                "description": "Stub created by auto-fixer",
                "inputSchema": {"type": "object", "properties": {}},
                "x_skillpulse_stub": True
            },
            {
                "name": "auto_stub_by_desc",
                "description": "[AUTO-GENERATED STUB] Placeholder tool",
                "inputSchema": {"type": "object", "properties": {}}
            }
        ]
    }
    report = MCPContractValidator.validate_tools_data(data, "stub_test.json")
    assert report.error_count == 0
    assert report.warning_count == 2
    assert "auto_stub_by_field" in report.stub_tools
    assert "auto_stub_by_desc" in report.stub_tools
    assert "live_tool" not in report.stub_tools

    # Verify tool models have is_stub set
    tools_by_name = {t.name: t for t in report.tools}
    assert tools_by_name["live_tool"].is_stub is False
    assert tools_by_name["auto_stub_by_field"].is_stub is True
    assert tools_by_name["auto_stub_by_desc"].is_stub is True

    # Verify MCP005 diagnostic issues emitted
    mcp005_issues = [i for i in report.issues if i.rule_id == "MCP005"]
    assert len(mcp005_issues) == 2
    assert all(i.severity == "WARNING" for i in mcp005_issues)

