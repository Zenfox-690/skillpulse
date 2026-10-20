"""
Deterministic MCP (2025-11-25) tool schema and skill contract validator.
Cross-checks declared MCP tools against prompt instructions in Agent Skills to detect
Ghost Tools, schema violations, and orphaned tools in sub-millisecond execution.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from skillpulse.models import DiagnosticIssue, MCPTool, MCPReport, SkillReport


class MCPConfigDiscovery:
    """Discovers MCP tool configuration files in a project workspace."""

    COMMON_FILENAMES = [
        "mcp_tools.json",
        "mcp.json",
        "tools.json",
        ".mcp_tools.json",
        "mcp_config.json",
        "claude_desktop_config.json",
    ]

    @classmethod
    def find_mcp_config(cls, workspace_root: Path) -> Optional[Path]:
        """Locates candidate MCP configuration file."""
        for name in cls.COMMON_FILENAMES:
            candidate = workspace_root / name
            if candidate.exists() and candidate.is_file():
                return candidate

        # Also search in .agents/ or examples/
        for sub in [".agents", "examples"]:
            subdir = workspace_root / sub
            if subdir.exists() and subdir.is_dir():
                for name in cls.COMMON_FILENAMES:
                    candidate = subdir / name
                    if candidate.exists() and candidate.is_file():
                        return candidate

        return None


class MCPContractValidator:
    """Validates MCP 2025-11-25 tool schemas and checks cross-contracts with skills."""

    @classmethod
    def validate_tools_data(
        cls,
        raw_data: Any,
        source_name: str = "mcp_tools.json",
        scanned_skills: Optional[List[SkillReport]] = None
    ) -> MCPReport:
        """Validates loaded JSON data against MCP 2025-11-25 specification."""
        issues: List[DiagnosticIssue] = []
        parsed_tools: List[MCPTool] = []
        tool_names = set()

        # Handle various wrapping envelopes (e.g. {"tools": [...]}, {"result": {"tools": [...]}}, or direct list)
        tools_list: Optional[List[Dict[str, Any]]] = None

        if isinstance(raw_data, list):
            tools_list = raw_data
        elif isinstance(raw_data, dict):
            if "tools" in raw_data and isinstance(raw_data["tools"], list):
                tools_list = raw_data["tools"]
            elif "result" in raw_data and isinstance(raw_data["result"], dict) and "tools" in raw_data["result"]:
                tools_list = raw_data["result"]["tools"]
            elif "mcpServers" in raw_data:
                # Configuration declaring server commands rather than tool exports
                issues.append(DiagnosticIssue(
                    rule_id="MCP001",
                    severity="INFO",
                    message="Found MCP client server definition mapping. Ensure tool schema exports are provided in 'tools' format.",
                    suggestion="Export the server's tools/list response to mcp_tools.json for static schema inspection."
                ))
                return MCPReport(source_file=source_name, protocol_version="2025-11-25", issues=issues)

        # Rule MCP001: Valid format
        if tools_list is None:
            issues.append(DiagnosticIssue(
                rule_id="MCP001",
                severity="ERROR",
                message="Invalid MCP tools format. Expected a JSON array of tools or object with 'tools' array.",
                suggestion="Format MCP tools as: {'tools': [{'name': '...', 'description': '...', 'inputSchema': {...}}]}"
            ))
            return MCPReport(source_file=source_name, protocol_version="2025-11-25", issues=issues)

        # Rule MCP002: Tool schema validation
        for idx, tool_dict in enumerate(tools_list, start=1):
            if not isinstance(tool_dict, dict):
                issues.append(DiagnosticIssue(
                    rule_id="MCP002",
                    severity="ERROR",
                    message=f"Tool item #{idx} is not a valid JSON object.",
                    suggestion="Each tool item must be an object with name, description, and inputSchema."
                ))
                continue

            name = tool_dict.get("name")
            desc = tool_dict.get("description", "")
            schema = tool_dict.get("inputSchema")

            # Check name
            if not name or not isinstance(name, str) or not name.strip():
                issues.append(DiagnosticIssue(
                    rule_id="MCP002",
                    severity="ERROR",
                    message=f"Tool item #{idx} is missing a required 'name' field.",
                    suggestion="Provide a non-empty name string for each tool."
                ))
                name = f"unnamed_tool_{idx}"
            else:
                name = name.strip()
                if name in tool_names:
                    issues.append(DiagnosticIssue(
                        rule_id="MCP002",
                        severity="ERROR",
                        message=f"Duplicate MCP tool name detected: '{name}'.",
                        suggestion="Ensure all declared tool names are unique."
                    ))
                tool_names.add(name)

            # Check description
            if not desc or not isinstance(desc, str) or not desc.strip():
                issues.append(DiagnosticIssue(
                    rule_id="MCP002",
                    severity="WARNING",
                    message=f"MCP tool '{name}' has an empty or missing description.",
                    suggestion="Add a detailed description explaining when and how the model should call this tool."
                ))

            # Check inputSchema
            if schema is None or not isinstance(schema, dict):
                issues.append(DiagnosticIssue(
                    rule_id="MCP002",
                    severity="ERROR",
                    message=f"MCP tool '{name}' is missing required 'inputSchema' object.",
                    suggestion="Add 'inputSchema: {\"type\": \"object\", \"properties\": {}}' adhering to MCP 2025-11-25."
                ))
                schema = {}
            else:
                schema_type = schema.get("type")
                if schema_type != "object":
                    issues.append(DiagnosticIssue(
                        rule_id="MCP002",
                        severity="ERROR",
                        message=f"MCP tool '{name}' inputSchema type must be 'object' (found '{schema_type}').",
                        suggestion="Set inputSchema.type to 'object' per JSON Schema Draft 7 / MCP specification."
                    ))

                props = schema.get("properties")
                if props is not None and not isinstance(props, dict):
                    issues.append(DiagnosticIssue(
                        rule_id="MCP002",
                        severity="ERROR",
                        message=f"MCP tool '{name}' inputSchema.properties must be an object.",
                        suggestion="Format properties as a dictionary mapping parameter names to types."
                    ))

                required_props = schema.get("required")
                if required_props is not None:
                    if not isinstance(required_props, list):
                        issues.append(DiagnosticIssue(
                            rule_id="MCP002",
                            severity="ERROR",
                            message=f"MCP tool '{name}' inputSchema.required must be an array of strings.",
                            suggestion="Set required to an array of property names, e.g. ['param1', 'param2']."
                        ))
                    elif isinstance(props, dict):
                        for req in required_props:
                            if req not in props:
                                issues.append(DiagnosticIssue(
                                    rule_id="MCP002",
                                    severity="WARNING",
                                    message=f"MCP tool '{name}' lists '{req}' as required, but it is not defined in properties.",
                                    suggestion=f"Add definition for '{req}' under inputSchema.properties."
                                ))

            parsed_tools.append(MCPTool(
                name=name,
                description=str(desc),
                input_schema=schema
            ))

        # Cross-Checking with Agent Skills
        ghost_tools = []
        orphan_tools = []

        if scanned_skills:
            all_referenced_tools = set()
            skill_tool_map: Dict[str, List[str]] = {}

            for skill in scanned_skills:
                for t in skill.referenced_tools:
                    all_referenced_tools.add(t)
                    skill_tool_map.setdefault(t, []).append(skill.name)

            # Rule MCP003: Ghost Tools (tools called in prompt instructions but missing from MCP tool declarations)
            # Only consider tool references that follow snake_case or standard tool naming and aren't builtins
            for ref_tool in sorted(list(all_referenced_tools)):
                # If tool name matches an obvious tool pattern (has underscore or matches known tool pattern)
                # and is not in declared MCP tools
                if "_" in ref_tool and ref_tool not in tool_names:
                    referencing_skills = ", ".join(skill_tool_map.get(ref_tool, []))
                    ghost_tools.append(ref_tool)
                    issues.append(DiagnosticIssue(
                        rule_id="MCP003",
                        severity="ERROR",
                        message=f"Ghost Tool detected: '{ref_tool}' is referenced in skill(s) [{referencing_skills}] but is not declared in MCP tools.",
                        suggestion=f"Define '{ref_tool}' in your MCP server tool manifest or correct the skill prompt instructions."
                    ))

            # Rule MCP004: Orphan Tools (declared in MCP tools but never referenced across any skills)
            for declared in sorted(list(tool_names)):
                if declared not in all_referenced_tools:
                    orphan_tools.append(declared)
                    issues.append(DiagnosticIssue(
                        rule_id="MCP004",
                        severity="WARNING",
                        message=f"Orphan MCP tool: '{declared}' is declared in MCP tools but never referenced in any Agent Skill.",
                        suggestion=f"Document '{declared}' in an agent skill prompt so agents know when to invoke it."
                    ))

        return MCPReport(
            source_file=source_name,
            protocol_version="2025-11-25",
            tools=parsed_tools,
            ghost_tools=ghost_tools,
            orphan_tools=orphan_tools,
            issues=issues
        )

    @classmethod
    def validate_file(cls, path: Path, scanned_skills: Optional[List[SkillReport]] = None) -> MCPReport:
        """Reads and validates an MCP tools JSON file."""
        try:
            content = path.read_text(encoding="utf-8")
            raw_data = json.loads(content)
            return cls.validate_tools_data(raw_data, str(path), scanned_skills)
        except json.JSONDecodeError as e:
            return MCPReport(
                source_file=str(path),
                protocol_version="2025-11-25",
                issues=[DiagnosticIssue(
                    rule_id="MCP001",
                    severity="ERROR",
                    message=f"Malformed JSON in MCP config: {e.msg} at line {e.lineno}, col {e.colno}",
                    suggestion="Fix JSON syntax errors in the MCP tools file."
                )]
            )
        except Exception as e:
            return MCPReport(
                source_file=str(path),
                protocol_version="2025-11-25",
                issues=[DiagnosticIssue(
                    rule_id="MCP001",
                    severity="ERROR",
                    message=f"Failed to read MCP config: {str(e)}",
                    suggestion="Ensure the file exists and is accessible."
                )]
            )
