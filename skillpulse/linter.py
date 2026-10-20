"""
Static linter and token estimator for Agent Skills (SKILL.md).
"""

from pathlib import Path
import re
from typing import List, Dict, Any, Tuple, Optional

from skillpulse.models import DiagnosticIssue, SkillReport


class SkillScanner:
    """Discovers SKILL.md files within a target directory."""

    @staticmethod
    def find_skills(root_path: Path) -> List[Path]:
        """Recursively locates all SKILL.md files under root_path."""
        if not root_path.exists():
            return []
        if root_path.is_file() and root_path.name.lower() == "skill.md":
            return [root_path]

        skill_files = []
        for path in root_path.rglob("*.md"):
            if path.name.lower() == "skill.md":
                skill_files.append(path)
        return sorted(skill_files)


class SimpleYAMLParser:
    """
    Lightweight, deterministic pure-Python YAML frontmatter parser.
    Zero C-extension dependency, supports keys, quoted strings, and list items.
    """

    @classmethod
    def parse(cls, yaml_text: str) -> Tuple[Dict[str, Any], List[DiagnosticIssue]]:
        data: Dict[str, Any] = {}
        issues: List[DiagnosticIssue] = []
        lines = yaml_text.splitlines()

        current_key: Optional[str] = None
        current_list: Optional[List[str]] = None

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # List item under current key
            if stripped.startswith("- ") and current_key:
                val = stripped[2:].strip().strip("\"'")
                if current_list is None:
                    current_list = []
                    data[current_key] = current_list
                current_list.append(val)
                continue

            # Key: value pair
            if ":" in stripped:
                # Flush previous list
                current_list = None
                key_part, val_part = stripped.split(":", 1)
                key = key_part.strip()
                val = val_part.strip()

                if not key:
                    issues.append(DiagnosticIssue(
                        rule_id="SKILL001",
                        severity="ERROR",
                        message="Empty YAML key name detected.",
                        line_number=idx,
                        suggestion="Provide a valid key name, e.g., 'name: my-skill'."
                    ))
                    continue

                # Strip quotes
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]

                # Inline list: [a, b, c]
                if val.startswith("[") and val.endswith("]"):
                    items = [i.strip().strip("\"'") for i in val[1:-1].split(",") if i.strip()]
                    data[key] = items
                    current_key = key
                elif val == "":
                    # Might be multiline or list to follow
                    data[key] = ""
                    current_key = key
                else:
                    data[key] = val
                    current_key = key
            else:
                if current_key and isinstance(data.get(current_key), str):
                    # Multiline string append
                    data[current_key] += " " + stripped
                else:
                    issues.append(DiagnosticIssue(
                        rule_id="SKILL001",
                        severity="ERROR",
                        message=f"Malformed YAML syntax on line: '{stripped}'",
                        line_number=idx,
                        suggestion="Ensure frontmatter lines follow 'key: value' format."
                    ))

        return data, issues


class SkillLinter:
    """Evaluates SKILL.md against Agent Skills specifications."""

    TRIGGER_KEYWORDS = [
        "when", "use this", "trigger", "activates", "run this",
        "activate", "call this", "invoke", "use when", "slash command",
        "intended for", "instructions for"
    ]

    TOOL_REF_REGEX = re.compile(r"`([a-zA-Z0-9_-]+)`|\b([a-zA-Z0-9_]+)\(")

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """Heuristic BPE token estimator (~1.3 tokens per word)."""
        words = len(text.split())
        return int(words * 1.3)

    @classmethod
    def extract_tool_references(cls, frontmatter: Dict[str, Any], body: str) -> List[str]:
        """Extracts tool names referenced in frontmatter or markdown prompt instructions."""
        tools = set()

        # Tools declared explicitly in frontmatter
        for key in ["tools", "allowed_tools", "mcp_tools", "requires_tools"]:
            if key in frontmatter:
                val = frontmatter[key]
                if isinstance(val, list):
                    for item in val:
                        tools.add(str(item).strip())
                elif isinstance(val, str):
                    tools.add(val.strip())

        # Tools referenced in markdown code snippets or tool calls
        matches = cls.TOOL_REF_REGEX.findall(body)
        for m1, m2 in matches:
            candidate = m1 or m2
            if candidate and len(candidate) > 2 and not candidate.isnumeric():
                # Avoid standard markdown / programming keywords
                if candidate.lower() not in {"bash", "python", "json", "true", "false", "null", "none", "self", "import"}:
                    tools.add(candidate)

        return sorted(list(tools))

    @classmethod
    def lint_text(cls, content: str, file_path: str = "SKILL.md") -> SkillReport:
        """Lints a SKILL.md string content and returns a SkillReport."""
        issues: List[DiagnosticIssue] = []
        token_count = cls.estimate_tokens(content)

        lines = content.splitlines()

        # Rule SKILL001: YAML Frontmatter delimiters
        if not lines or lines[0].strip() != "---":
            issues.append(DiagnosticIssue(
                rule_id="SKILL001",
                severity="ERROR",
                message="Missing opening frontmatter delimiter '---' on line 1.",
                line_number=1,
                suggestion="Add '---' as the very first line of the file."
            ))
            return SkillReport(
                file_path=file_path,
                is_valid=False,
                token_count=token_count,
                issues=issues
            )

        # Find closing delimiter
        closing_idx = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                closing_idx = i
                break

        if closing_idx == -1:
            issues.append(DiagnosticIssue(
                rule_id="SKILL001",
                severity="ERROR",
                message="Missing closing frontmatter delimiter '---'.",
                line_number=len(lines),
                suggestion="Add a closing '---' after the metadata block."
            ))
            return SkillReport(
                file_path=file_path,
                is_valid=False,
                token_count=token_count,
                issues=issues
            )

        frontmatter_text = "\n".join(lines[1:closing_idx])
        body_text = "\n".join(lines[closing_idx + 1:])

        frontmatter, parse_issues = SimpleYAMLParser.parse(frontmatter_text)
        issues.extend(parse_issues)

        # Rule SKILL002: Name attribute
        name = frontmatter.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            issues.append(DiagnosticIssue(
                rule_id="SKILL002",
                severity="ERROR",
                message="Missing required frontmatter attribute 'name'.",
                suggestion="Add 'name: my-skill-name' to the YAML frontmatter."
            ))
            skill_name = "unknown"
        else:
            skill_name = name.strip()
            if len(skill_name) > 64:
                issues.append(DiagnosticIssue(
                    rule_id="SKILL002",
                    severity="ERROR",
                    message=f"Skill name '{skill_name}' exceeds 64 characters ({len(skill_name)} chars).",
                    suggestion="Shorten the skill name to under 64 characters."
                ))
            if not re.match(r"^[a-zA-Z0-9_\-\.]+$", skill_name):
                issues.append(DiagnosticIssue(
                    rule_id="SKILL002",
                    severity="WARNING",
                    message=f"Skill name '{skill_name}' contains special characters or spaces.",
                    suggestion="Use lowercase alphanumeric characters and hyphens/underscores."
                ))

        # Rule SKILL003: Description attribute
        desc = frontmatter.get("description")
        if not desc or not isinstance(desc, str) or not desc.strip():
            issues.append(DiagnosticIssue(
                rule_id="SKILL003",
                severity="ERROR",
                message="Missing required frontmatter attribute 'description'.",
                suggestion="Add 'description: Clear, action-oriented purpose of this skill' to frontmatter."
            ))
            description = ""
        else:
            description = desc.strip()
            if len(description) < 15:
                issues.append(DiagnosticIssue(
                    rule_id="SKILL003",
                    severity="WARNING",
                    message="Skill description is very brief (< 15 characters).",
                    suggestion="Provide more detail on what the skill does and when to activate it."
                ))

        # Rule SKILL004: Trigger Guidance
        combined_text = (description + " " + body_text).lower()
        has_trigger = any(trigger in combined_text for trigger in cls.TRIGGER_KEYWORDS)
        if not has_trigger:
            issues.append(DiagnosticIssue(
                rule_id="SKILL004",
                severity="WARNING",
                message="No explicit trigger phrase or activation condition detected.",
                suggestion="Add trigger phrases such as 'Use when the user asks...' or 'Trigger on...'"
            ))

        # Rule SKILL005: Token Budget
        if token_count > 2500:
            issues.append(DiagnosticIssue(
                rule_id="SKILL005",
                severity="WARNING",
                message=f"High prompt token estimate: ~{token_count} tokens (exceeds recommended 2,500 budget).",
                suggestion="Refactor verbose prompt instructions into reference files to save agent context budget."
            ))

        referenced_tools = cls.extract_tool_references(frontmatter, body_text)
        is_valid = not any(i.severity == "ERROR" for i in issues)

        return SkillReport(
            file_path=file_path,
            name=skill_name,
            description=description,
            is_valid=is_valid,
            token_count=token_count,
            referenced_tools=referenced_tools,
            issues=issues
        )

    @classmethod
    def lint_file(cls, path: Path) -> SkillReport:
        """Reads and lints a single SKILL.md file."""
        try:
            content = path.read_text(encoding="utf-8")
            return cls.lint_text(content, str(path))
        except Exception as e:
            return SkillReport(
                file_path=str(path),
                is_valid=False,
                issues=[DiagnosticIssue(
                    rule_id="SKILL001",
                    severity="ERROR",
                    message=f"Failed to read file: {str(e)}",
                    suggestion="Ensure the file is readable UTF-8 text."
                )]
            )
