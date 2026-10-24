"""
Data models and dataclass schemas for skillpulse.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class DiagnosticIssue:
    """Represents a single diagnostic lint or schema issue."""
    rule_id: str
    severity: str  # "ERROR", "WARNING", "INFO"
    message: str
    line_number: Optional[int] = None
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "line_number": self.line_number,
            "suggestion": self.suggestion,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DiagnosticIssue":
        return cls(
            rule_id=data.get("rule_id", "UNKNOWN"),
            severity=data.get("severity", "ERROR"),
            message=data.get("message", ""),
            line_number=data.get("line_number"),
            suggestion=data.get("suggestion", ""),
        )


@dataclass
class SkillReport:
    """Represents diagnostic findings for a single SKILL.md file."""
    file_path: str
    name: str = ""
    description: str = ""
    is_valid: bool = True
    token_count: int = 0
    referenced_tools: List[str] = field(default_factory=list)
    issues: List[DiagnosticIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "WARNING")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "name": self.name,
            "description": self.description,
            "is_valid": self.is_valid,
            "token_count": self.token_count,
            "referenced_tools": self.referenced_tools,
            "issues": [i.to_dict() for i in self.issues],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillReport":
        issues = [DiagnosticIssue.from_dict(i) for i in data.get("issues", [])]
        return cls(
            file_path=data.get("file_path", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            is_valid=data.get("is_valid", True),
            token_count=data.get("token_count", 0),
            referenced_tools=data.get("referenced_tools", []),
            issues=issues,
        )


@dataclass
class MCPTool:
    """Represents a declared tool under MCP 2025-11-25 specifications."""
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    is_stub: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "is_stub": self.is_stub,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPTool":
        is_stub = bool(data.get("is_stub", False) or "[AUTO-GENERATED STUB]" in str(data.get("description", "")) or data.get("x_skillpulse_stub") is True)
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            input_schema=data.get("input_schema", {}),
            is_stub=is_stub,
        )


@dataclass
class MCPReport:
    """Represents validation findings for MCP tool definitions and skill contracts."""
    source_file: str
    protocol_version: str = "2025-11-25"
    tools: List[MCPTool] = field(default_factory=list)
    ghost_tools: List[str] = field(default_factory=list)
    orphan_tools: List[str] = field(default_factory=list)
    stub_tools: List[str] = field(default_factory=list)
    issues: List[DiagnosticIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "WARNING")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_file": self.source_file,
            "protocol_version": self.protocol_version,
            "tools": [t.to_dict() for t in self.tools],
            "ghost_tools": self.ghost_tools,
            "orphan_tools": self.orphan_tools,
            "stub_tools": self.stub_tools,
            "issues": [i.to_dict() for i in self.issues],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPReport":
        tools = [MCPTool.from_dict(t) for t in data.get("tools", [])]
        issues = [DiagnosticIssue.from_dict(i) for i in data.get("issues", [])]
        return cls(
            source_file=data.get("source_file", ""),
            protocol_version=data.get("protocol_version", "2025-11-25"),
            tools=tools,
            ghost_tools=data.get("ghost_tools", []),
            orphan_tools=data.get("orphan_tools", []),
            stub_tools=data.get("stub_tools", []),
            issues=issues,
        )


@dataclass
class ScanResult:
    """Composite result of a skillpulse scan."""
    timestamp: str
    workspace_path: str
    health_score: int
    grade: str
    skills: List[SkillReport] = field(default_factory=list)
    mcp_report: Optional[MCPReport] = None

    @property
    def total_errors(self) -> int:
        count = sum(s.error_count for s in self.skills)
        if self.mcp_report:
            count += self.mcp_report.error_count
        return count

    @property
    def total_warnings(self) -> int:
        count = sum(s.warning_count for s in self.skills)
        if self.mcp_report:
            count += self.mcp_report.warning_count
        return count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "workspace_path": self.workspace_path,
            "health_score": self.health_score,
            "grade": self.grade,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "skills": [s.to_dict() for s in self.skills],
            "mcp_report": self.mcp_report.to_dict() if self.mcp_report else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScanResult":
        skills = [SkillReport.from_dict(s) for s in data.get("skills", [])]
        mcp_data = data.get("mcp_report")
        mcp_report = MCPReport.from_dict(mcp_data) if mcp_data else None
        return cls(
            timestamp=data.get("timestamp", ""),
            workspace_path=data.get("workspace_path", ""),
            health_score=data.get("health_score", 0),
            grade=data.get("grade", "F"),
            skills=skills,
            mcp_report=mcp_report,
        )

