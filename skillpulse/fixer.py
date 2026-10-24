"""
Deterministic contract auto-fixer for Agent Skills and MCP 2025-11-25 schemas.
Provides idempotent, atomic remediations for common lint and schema defects.
"""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import shutil
from typing import List, Dict, Any, Optional, Tuple

from skillpulse.linter import SkillScanner, SkillLinter
from skillpulse.mcp_tester import MCPConfigDiscovery, MCPContractValidator
from skillpulse.models import ScanResult
from skillpulse.scorer import HealthScorer


@dataclass
class FixAction:
    """Represents an individual repair action proposed or performed."""
    rule_id: str
    target_file: str
    description: str
    applied: bool = False
    diff_summary: str = ""


@dataclass
class FixResult:
    """Summary of fixes proposed or applied across a workspace."""
    workspace_path: str
    dry_run: bool
    actions: List[FixAction] = field(default_factory=list)
    pre_scan: Optional[ScanResult] = None
    post_scan: Optional[ScanResult] = None

    @property
    def total_actions(self) -> int:
        return len(self.actions)


class WorkspaceFixer:
    """
    Inspects workspace skills and MCP tools manifests to remediate:
    - MCP003: Ghost tools (adds valid MCP 2025-11-25 placeholder stubs)
    - MCP002: Broken tool schemas (repairs missing or non-object inputSchema)
    - SKILL003: Missing skill descriptions (injects trigger-compliant default)
    """

    DEFAULT_SKILL_DESCRIPTION = 'description: "Use this skill when performing automated workflow tasks."'

    def __init__(
        self,
        workspace_root: Path,
        skills_dir: Optional[Path] = None,
        mcp_config_path: Optional[Path] = None,
        dry_run: bool = False,
        output_dir: Optional[Path] = None,
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.dry_run = dry_run
        self.output_dir = Path(output_dir).resolve() if output_dir else None

        # If output_dir is specified and distinct, prepare copy
        if self.output_dir and self.output_dir != self.workspace_root:
            self._prepare_output_directory(skills_dir, mcp_config_path)
            # Rebase paths to output_dir
            self.target_root = self.output_dir
            self.target_skills_dir = self.output_dir / "skills" if (self.output_dir / "skills").exists() else self.output_dir
            self.target_mcp_config = self._find_target_mcp_config()
        else:
            self.target_root = self.workspace_root
            self.target_skills_dir = Path(skills_dir).resolve() if skills_dir else self.workspace_root
            self.target_mcp_config = Path(mcp_config_path).resolve() if mcp_config_path else MCPConfigDiscovery.find_mcp_config(self.workspace_root)

    def _prepare_output_directory(self, skills_dir: Optional[Path], mcp_config_path: Optional[Path]):
        """Safely clones workspace fixtures into target output_dir without mutating originals."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Source paths
        src_skills = Path(skills_dir).resolve() if skills_dir else self.workspace_root
        src_mcp = Path(mcp_config_path).resolve() if mcp_config_path else MCPConfigDiscovery.find_mcp_config(self.workspace_root)

        # Copy skills
        dest_skills = self.output_dir / "skills"
        if src_skills.is_dir():
            if dest_skills.exists():
                shutil.rmtree(dest_skills)
            shutil.copytree(src_skills, dest_skills)
        elif src_skills.is_file():
            dest_skills.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_skills, dest_skills / src_skills.name)

        # Copy MCP config
        if src_mcp and src_mcp.exists():
            shutil.copy2(src_mcp, self.output_dir / src_mcp.name)

    def _find_target_mcp_config(self) -> Optional[Path]:
        for name in MCPConfigDiscovery.COMMON_FILENAMES:
            candidate = self.target_root / name
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    @staticmethod
    def _atomic_write_text(target: Path, content: str):
        """Performs atomic file replacement on disk."""
        tmp = target.with_suffix(f".tmp_fix_{os.getpid()}")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(target)

    def run_scan(self, skills_dir: Path, mcp_path: Optional[Path]) -> ScanResult:
        """Executes a diagnostic scan on target directory and returns ScanResult."""
        skill_files = SkillScanner.find_skills(skills_dir)
        skill_reports = [SkillLinter.lint_file(p) for p in skill_files]

        mcp_report = None
        if mcp_path and mcp_path.exists():
            mcp_report = MCPContractValidator.validate_file(mcp_path, skill_reports)

        return HealthScorer.score_scan(skill_reports, mcp_report, str(self.target_root))

    def fix(self) -> FixResult:
        """Performs diagnosis and applies or simulates deterministic remediations."""
        actions: List[FixAction] = []

        # 1. Pre-fix scan
        pre_scan = self.run_scan(self.target_skills_dir, self.target_mcp_config)

        # 2. Fix SKILL.md files (SKILL003: missing description)
        for skill in pre_scan.skills:
            has_desc_error = any(i.rule_id == "SKILL003" and i.severity == "ERROR" for i in skill.issues)
            if has_desc_error:
                action = self._fix_skill_description(Path(skill.file_path))
                if action:
                    actions.append(action)

        # 3. Fix MCP Tools (MCP002: broken schema & MCP003: ghost tools)
        if pre_scan.mcp_report and self.target_mcp_config and self.target_mcp_config.exists():
            mcp_actions = self._fix_mcp_config(self.target_mcp_config, pre_scan)
            actions.extend(mcp_actions)

        # 4. Post-fix scan (if dry-run, simulate by running scan on in-memory or reporting actual)
        post_scan = self.run_scan(self.target_skills_dir, self.target_mcp_config)

        return FixResult(
            workspace_path=str(self.target_root),
            dry_run=self.dry_run,
            actions=actions,
            pre_scan=pre_scan,
            post_scan=post_scan,
        )

    def _fix_skill_description(self, skill_path: Path) -> Optional[FixAction]:
        """Injects a valid description into YAML frontmatter if missing."""
        try:
            content = skill_path.read_text(encoding="utf-8")
        except Exception:
            return None

        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            return None

        # Locate closing frontmatter delimiter
        closing_idx = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                closing_idx = i
                break

        if closing_idx == -1:
            return None

        # Check if description already exists in frontmatter
        for line in lines[1:closing_idx]:
            if line.strip().startswith("description:"):
                return None  # Already present

        # Inject description right after opening '---'
        new_lines = [lines[0], self.DEFAULT_SKILL_DESCRIPTION] + lines[1:]
        new_content = "\n".join(new_lines) + ("\n" if content.endswith("\n") else "")

        diff_summary = f"+ {self.DEFAULT_SKILL_DESCRIPTION} (under frontmatter)"

        if not self.dry_run:
            self._atomic_write_text(skill_path, new_content)

        return FixAction(
            rule_id="SKILL003",
            target_file=str(skill_path),
            description="Injected compliant default 'description' attribute into YAML frontmatter.",
            applied=not self.dry_run,
            diff_summary=diff_summary,
        )

    def _fix_mcp_config(self, mcp_path: Path, pre_scan: ScanResult) -> List[FixAction]:
        """Repairs schema defects (MCP002) and adds placeholder stubs for ghost tools (MCP003)."""
        actions: List[FixAction] = []

        try:
            raw_text = mcp_path.read_text(encoding="utf-8")
            data = json.loads(raw_text)
        except Exception:
            return actions

        modified = False

        # Locate tools array within JSON structure
        tools_list: Optional[List[Dict[str, Any]]] = None
        wrap_key: Optional[str] = None

        if isinstance(data, list):
            tools_list = data
        elif isinstance(data, dict):
            if "tools" in data and isinstance(data["tools"], list):
                tools_list = data["tools"]
                wrap_key = "tools"
            elif "result" in data and isinstance(data["result"], dict) and "tools" in data["result"]:
                tools_list = data["result"]["tools"]
                wrap_key = "result.tools"

        if tools_list is None:
            return actions

        # 1. Remediate MCP002: Broken schemas
        for idx, tool in enumerate(tools_list):
            if not isinstance(tool, dict):
                continue

            name = tool.get("name", f"unnamed_tool_{idx + 1}")
            schema = tool.get("inputSchema")

            # Missing or non-object inputSchema
            if schema is None or not isinstance(schema, dict) or schema.get("type") != "object":
                tool["inputSchema"] = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
                modified = True
                actions.append(FixAction(
                    rule_id="MCP002",
                    target_file=str(mcp_path),
                    description=f"Repaired missing or invalid 'inputSchema' on tool '{name}' to valid MCP 2025-11-25 object schema.",
                    applied=not self.dry_run,
                    diff_summary=f"tool '{name}': inputSchema repaired to {{'type': 'object', 'properties': {{}}, 'required': []}}"
                ))

            # Missing description
            desc = tool.get("description")
            if not desc or not isinstance(desc, str) or not desc.strip():
                tool["description"] = f"[AUTO-GENERATED STUB] Implement '{name}' tool for MCP 2025-11-25."
                modified = True
                actions.append(FixAction(
                    rule_id="MCP002",
                    target_file=str(mcp_path),
                    description=f"Added placeholder description for tool '{name}'. Note: Implementation is required before use.",
                    applied=not self.dry_run,
                    diff_summary=f"tool '{name}': description set to placeholder stub"
                ))

        # 2. Remediate MCP003: Ghost tools
        existing_names = {t.get("name") for t in tools_list if isinstance(t, dict) and "name" in t}

        ghost_tools = pre_scan.mcp_report.ghost_tools if pre_scan.mcp_report else []
        for ghost in ghost_tools:
            if ghost not in existing_names:
                stub_tool = {
                    "name": ghost,
                    "description": f"[AUTO-GENERATED STUB] Placeholder for '{ghost}'. Implementation required for MCP 2025-11-25.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    },
                    "x_skillpulse_stub": True
                }
                tools_list.append(stub_tool)
                existing_names.add(ghost)
                modified = True
                actions.append(FixAction(
                    rule_id="MCP003",
                    target_file=str(mcp_path),
                    description=f"Generated MCP 2025-11-25 placeholder stub for ghost tool '{ghost}'. Note: Placeholder only; requires implementation.",
                    applied=not self.dry_run,
                    diff_summary=f"+ Tool stub '{ghost}' added with object inputSchema"
                ))

        if modified and not self.dry_run:
            new_text = json.dumps(data, indent=2) + "\n"
            self._atomic_write_text(mcp_path, new_text)

        return actions
