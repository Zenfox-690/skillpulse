"""
Command-line interface and terminal renderer for skillpulse.
Supports text, machine-readable JSON, and GitHub/GitLab PR Markdown formats,
alongside deterministic contract auto-fixing and offline report generation.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import List, Optional, Dict, Any

from skillpulse.linter import SkillScanner, SkillLinter
from skillpulse.mcp_tester import MCPConfigDiscovery, MCPContractValidator
from skillpulse.scorer import HealthScorer
from skillpulse.models import SkillReport, MCPReport, ScanResult, DiagnosticIssue

# Ensure UTF-8 output on Windows consoles if supported
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Terminal ANSI Colors
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
GRAY = "\033[90m"


def print_banner():
    banner = rf"""
{CYAN}{BOLD}  ___ _   _ _ _                 _          
 / __| |_(_) | |_ __ _  _ | |___ ___ 
 \__ \ / / | | | '_ \ || | | (_-< / -_)
 |___/_\_\_|_|_| .__/\_,_|_|_/__/_\___|
               |_|                     {RESET}
 {GRAY}AI Agent Skills & MCP (2025-11-25) Linter & Test Harness{RESET}
"""
    print(banner)


def format_issue(issue: DiagnosticIssue) -> str:
    if issue.severity == "ERROR":
        tag = f"{RED}{BOLD}[ERROR]{RESET}"
    elif issue.severity == "WARNING":
        tag = f"{YELLOW}{BOLD}[WARN] {RESET}"
    else:
        tag = f"{CYAN}[INFO] {RESET}"

    line_info = f" [line {issue.line_number}]" if issue.line_number else ""
    out = f"    {tag} {BOLD}{issue.rule_id}{RESET}{line_info}: {issue.message}\n"
    if issue.suggestion:
        out += f"      {GRAY}-> Fix: {issue.suggestion}{RESET}\n"
    return out


def render_skill_reports(reports: List[SkillReport]) -> int:
    """Renders skill diagnostic reports to stdout and returns total error count."""
    total_errors = 0
    total_warnings = 0

    print(f"{BOLD}=== Agent Skills Validation ==={RESET}\n")

    if not reports:
        print(f"  {YELLOW}No SKILL.md files detected.{RESET}\n")
        return 0

    for rep in reports:
        status_symbol = f"{GREEN}[OK]{RESET}" if rep.is_valid else f"{RED}[FAIL]{RESET}"
        token_badge = f"{GRAY}(~{rep.token_count} tokens){RESET}"
        print(f"  {status_symbol} {BOLD}{rep.name}{RESET} {token_badge}")
        print(f"    {GRAY}Path: {rep.file_path}{RESET}")

        if rep.referenced_tools:
            tools_str = ", ".join(rep.referenced_tools)
            print(f"    {GRAY}Referenced Tools: {tools_str}{RESET}")

        if rep.issues:
            for issue in rep.issues:
                print(format_issue(issue), end="")
                if issue.severity == "ERROR":
                    total_errors += 1
                elif issue.severity == "WARNING":
                    total_warnings += 1
        else:
            print(f"    {GREEN}All rules passed.{RESET}")
        print()

    print(f"  Summary: {BOLD}{len(reports)}{RESET} skills checked, "
          f"{RED}{total_errors} errors{RESET}, {YELLOW}{total_warnings} warnings{RESET}.\n")

    return total_errors


def render_mcp_report(report: MCPReport) -> int:
    """Renders MCP diagnostic report to stdout and returns total error count."""
    print(f"{BOLD}=== Model Context Protocol (MCP 2025-11-25) Validation ==={RESET}\n")
    print(f"  {GRAY}Source: {report.source_file}{RESET}")
    print(f"  {GRAY}Protocol Standard: {report.protocol_version}{RESET}")
    print(f"  {BOLD}Declared Tools ({len(report.tools)}):{RESET}")

    for tool in report.tools:
        props = list(tool.input_schema.get("properties", {}).keys())
        params_str = f"({', '.join(props)})" if props else "(no params)"
        print(f"    {CYAN}* {tool.name}{RESET} {GRAY}{params_str}{RESET}")

    if not report.tools and not report.issues:
        print(f"    {YELLOW}No tools declared in configuration.{RESET}")

    print()

    if report.ghost_tools:
        print(f"  {RED}{BOLD}Ghost Tools Detected ({len(report.ghost_tools)}):{RESET}")
        for ghost in report.ghost_tools:
            print(f"    {RED}! {ghost} (referenced in skills, but missing in MCP tools){RESET}")
        print()

    if report.orphan_tools:
        print(f"  {YELLOW}{BOLD}Orphaned / Undocumented Tools ({len(report.orphan_tools)}):{RESET}")
        for orphan in report.orphan_tools:
            print(f"    {YELLOW}? {orphan} (declared in MCP, never referenced in skills){RESET}")
        print()

    if report.stub_tools:
        print(f"  {YELLOW}{BOLD}Unimplemented Placeholder Stubs ({len(report.stub_tools)}):{RESET}")
        for stub in report.stub_tools:
            print(f"    {YELLOW}⚠ {stub} (auto-generated stub schema; backend implementation required){RESET}")
        print()

    total_errors = 0
    total_warnings = 0
    if report.issues:
        print(f"  {BOLD}Diagnostics:{RESET}")
        for issue in report.issues:
            print(format_issue(issue), end="")
            if issue.severity == "ERROR":
                total_errors += 1
            elif issue.severity == "WARNING":
                total_warnings += 1
        print()
    else:
        print(f"  {GREEN}All MCP schema rules passed.{RESET}\n")

    print(f"  Summary: {BOLD}{len(report.tools)}{RESET} tools validated, "
          f"{RED}{total_errors} errors{RESET}, {YELLOW}{total_warnings} warnings{RESET}.\n")

    return total_errors


def render_scan_summary(scan: ScanResult):
    """Renders final executive health score summary block."""
    if scan.health_score >= 90:
        color = GREEN
    elif scan.health_score >= 80:
        color = CYAN
    elif scan.health_score >= 70:
        color = YELLOW
    elif scan.health_score >= 60:
        color = YELLOW
    else:
        color = RED

    formula_str = HealthScorer.format_formula(scan.total_errors, scan.total_warnings, scan.health_score, scan.grade)

    print(f"{BOLD}===================================================={RESET}")
    print(f"  {BOLD}Ecosystem Health Score:{RESET} {color}{BOLD}{scan.health_score}%{RESET} ({scan.grade})")
    print(f"  {GRAY}{HealthScorer.grade_description(scan.grade, scan.total_errors)}{RESET}")
    print(f"  {GRAY}Score Formula: {formula_str}{RESET}")
    print(f"  {BOLD}Total Critical Errors:{RESET} {RED if scan.total_errors else GREEN}{scan.total_errors}{RESET}")
    print(f"  {BOLD}Total Warnings:{RESET} {YELLOW if scan.total_warnings else GREEN}{scan.total_warnings}{RESET}")
    if scan.mcp_report:
        ghost_count = len(scan.mcp_report.ghost_tools)
        orphan_count = len(scan.mcp_report.orphan_tools)
        stub_count = len(scan.mcp_report.stub_tools)
        ghost_color = RED if ghost_count else GREEN
        orphan_color = YELLOW if orphan_count else GREEN
        stub_color = YELLOW if stub_count else GREEN
        print(f"  {BOLD}Ghost Tools:{RESET} {ghost_color}{ghost_count}{RESET} | {BOLD}Orphan Tools:{RESET} {orphan_color}{orphan_count}{RESET} | {BOLD}Schema Stubs:{RESET} {stub_color}{stub_count}{RESET}")
    print(f"{BOLD}===================================================={RESET}\n")


def render_markdown_summary(scan: ScanResult) -> str:
    """Generates clean GitHub/GitLab PR/MR comment summary table in Markdown."""
    lines = []
    lines.append("## 🔍 SkillPulse Diagnostics & Health Summary")
    lines.append("")
    status_label = "✅ PASSED" if scan.total_errors == 0 else "❌ CRITICAL ERRORS DETECTED"
    lines.append(f"**Health Score:** `{scan.health_score}%` (**Grade {scan.grade}**) &nbsp;|&nbsp; **Status:** {status_label}")
    lines.append("")
    lines.append("| Metric | Value | Status |")
    lines.append("| :--- | :--- | :--- |")
    lines.append(f"| **Ecosystem Health** | `{scan.health_score}%` (Grade {scan.grade}) | {'🟢 Ready' if scan.health_score >= 80 else '🔴 Action Required'} |")
    lines.append(f"| **Agent Skills Scanned** | `{len(scan.skills)}` | 📦 Inspected |")
    total_tools = len(scan.mcp_report.tools) if scan.mcp_report else 0
    lines.append(f"| **MCP Tools Verified** | `{total_tools}` | ⚙️ Protocol 2025-11-25 |")
    lines.append(f"| **Critical Errors** | `{scan.total_errors}` | {'🟢 0 errors' if scan.total_errors == 0 else '🔴 Blocks CI'} |")
    lines.append(f"| **Warnings / Cues** | `{scan.total_warnings}` | {'🟢 Clean' if scan.total_warnings == 0 else '🟡 Review'} |")
    if scan.mcp_report:
        ghosts = len(scan.mcp_report.ghost_tools)
        orphans = len(scan.mcp_report.orphan_tools)
        stubs = len(scan.mcp_report.stub_tools)
        lines.append(f"| **Ghost Tools (MCP003)** | `{ghosts}` | {'🟢 None' if ghosts == 0 else '🔴 Undefined calls'} |")
        lines.append(f"| **Orphan Tools (MCP004)** | `{orphans}` | {'🟢 None' if orphans == 0 else '🟡 Unreferenced'} |")
        lines.append(f"| **Placeholder Stubs (MCP005)** | `{stubs}` | {'🟢 None' if stubs == 0 else '🟡 Unimplemented'} |")
    lines.append("")

    all_issues = []
    for skill in scan.skills:
        for iss in skill.issues:
            all_issues.append((skill.file_path, iss))
    if scan.mcp_report:
        for iss in scan.mcp_report.issues:
            all_issues.append((scan.mcp_report.source_file, iss))

    if all_issues:
        lines.append("### 📋 Diagnostic Findings")
        lines.append("")
        lines.append("| Severity | Rule | Location | Description | Remediation |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for source, iss in all_issues:
            sev_badge = "🔴 ERROR" if iss.severity == "ERROR" else ("🟡 WARN" if iss.severity == "WARNING" else "🔵 INFO")
            loc = Path(source).name
            if iss.line_number:
                loc += f":L{iss.line_number}"
            clean_msg = iss.message.replace("|", "\\|")
            clean_fix = iss.suggestion.replace("|", "\\|")
            lines.append(f"| {sev_badge} | `{iss.rule_id}` | `{loc}` | {clean_msg} | {clean_fix} |")
        lines.append("")
    else:
        lines.append("> ✅ **All Agent Skills and MCP tool schemas passed validation cleanly with zero errors.**")
        lines.append("")

    formula_str = HealthScorer.format_formula(scan.total_errors, scan.total_warnings, scan.health_score, scan.grade)
    lines.append(f"**Score Breakdown:** `{formula_str}`")
    lines.append("")
    lines.append("---")
    lines.append(f"*Generated by [SkillPulse](https://github.com/Zenfox-690/skillpulse) on `{scan.timestamp or 'Live Run'}`*")
    return "\n".join(lines)


def _handle_json_output(filepath: Optional[str], data: Dict[str, Any]):
    """Writes machine-readable JSON data to file if --json-output was provided."""
    if filepath:
        out_path = Path(filepath).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def cmd_lint_skills(args: argparse.Namespace) -> int:
    """Executes skill linter only."""
    fmt = getattr(args, "format", "text")
    if fmt == "text":
        print_banner()

    target_path = Path(args.path).resolve()
    skill_files = SkillScanner.find_skills(target_path)
    reports = [SkillLinter.lint_file(p) for p in skill_files]
    total_errors = sum(r.error_count for r in reports)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scan_result = HealthScorer.score_scan(reports, None, str(target_path), timestamp)

    _handle_json_output(getattr(args, "json_output", None), scan_result.to_dict())

    if fmt == "json":
        print(json.dumps(scan_result.to_dict(), indent=2))
        return 1 if total_errors > 0 else 0
    elif fmt == "markdown":
        print(render_markdown_summary(scan_result))
        return 1 if total_errors > 0 else 0

    render_skill_reports(reports)
    return 1 if total_errors > 0 else 0


def cmd_test_mcp(args: argparse.Namespace) -> int:
    """Executes MCP tool schema and contract validation."""
    fmt = getattr(args, "format", "text")
    if fmt == "text":
        print_banner()

    config_path = Path(args.config).resolve()

    if not config_path.exists():
        discovered = MCPConfigDiscovery.find_mcp_config(Path.cwd())
        if discovered:
            config_path = discovered
        else:
            if fmt == "json":
                err_dict = {"error": f"MCP config not found at '{args.config}'", "total_errors": 1}
                print(json.dumps(err_dict, indent=2))
            else:
                print(f"{RED}Error: MCP config not found at '{args.config}' and none discovered in workspace.{RESET}")
            return 1

    scanned_skills = []
    if getattr(args, "skills_dir", None):
        skills_path = Path(args.skills_dir).resolve()
        skill_files = SkillScanner.find_skills(skills_path)
        scanned_skills = [SkillLinter.lint_file(p) for p in skill_files]
    elif (config_path.parent / "skills").is_dir():
        skill_files = SkillScanner.find_skills(config_path.parent / "skills")
        scanned_skills = [SkillLinter.lint_file(p) for p in skill_files]

    report = MCPContractValidator.validate_file(config_path, scanned_skills)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scan_result = HealthScorer.score_scan(scanned_skills, report, str(config_path.parent), timestamp)

    _handle_json_output(getattr(args, "json_output", None), scan_result.to_dict())

    if fmt == "json":
        print(json.dumps(scan_result.to_dict(), indent=2))
        return 1 if report.error_count > 0 else 0
    elif fmt == "markdown":
        print(render_markdown_summary(scan_result))
        return 1 if report.error_count > 0 else 0

    errors = render_mcp_report(report)
    return 1 if errors > 0 else 0


def cmd_scan(args: argparse.Namespace) -> int:
    """Executes full unified scan (Skills + MCP) and prints health score."""
    fmt = getattr(args, "format", "text")
    if fmt == "text":
        print_banner()

    workspace_root = Path(args.path).resolve()

    # 1. Discover and lint skills
    skills_dir = Path(args.skills_dir).resolve() if args.skills_dir else workspace_root
    skill_files = SkillScanner.find_skills(skills_dir)
    skill_reports = [SkillLinter.lint_file(p) for p in skill_files]

    # 2. Discover and validate MCP config
    mcp_report: Optional[MCPReport] = None
    if args.mcp_config:
        mcp_path = Path(args.mcp_config).resolve()
    else:
        mcp_path = MCPConfigDiscovery.find_mcp_config(workspace_root)

    if mcp_path and mcp_path.exists():
        mcp_report = MCPContractValidator.validate_file(mcp_path, skill_reports)

    # 3. Calculate health score
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scan_result = HealthScorer.score_scan(skill_reports, mcp_report, str(workspace_root), timestamp)

    # 4. Handle independent --json-output file write
    _handle_json_output(getattr(args, "json_output", None), scan_result.to_dict())

    # 5. Output handling based on --format
    if fmt == "json":
        # Pure JSON to stdout without banners
        print(json.dumps(scan_result.to_dict(), indent=2))
        return 1 if scan_result.total_errors > 0 else 0
    elif fmt == "markdown":
        # Pure Markdown PR table to stdout without banners
        print(render_markdown_summary(scan_result))
        return 1 if scan_result.total_errors > 0 else 0

    # Text / ANSI output
    render_skill_reports(skill_reports)
    if mcp_report:
        render_mcp_report(mcp_report)
    else:
        print(f"{BOLD}=== Model Context Protocol (MCP) ==={RESET}\n")
        print(f"  {YELLOW}No MCP tool definition file (mcp_tools.json) found.{RESET}\n")

    render_scan_summary(scan_result)

    # Generate HTML report if requested
    report_path = Path(args.report).resolve()
    try:
        from skillpulse.reporter import HTMLReporter
        HTMLReporter.generate(scan_result, report_path)
        print(f"  {GREEN}[OK] Visual diagnostic report generated:{RESET} {CYAN}{report_path}{RESET}\n")
    except ImportError:
        pass

    return 1 if scan_result.total_errors > 0 else 0


def cmd_report(args: argparse.Namespace) -> int:
    """Generates visual HTML report from full scan or saved JSON results."""
    from_json_path = getattr(args, "from_json", None) or getattr(args, "input", None)
    out_path = Path(args.output).resolve()

    if from_json_path and (from_json_path.endswith(".json") or getattr(args, "from_json", None)):
        json_file = Path(from_json_path).resolve()
        if not json_file.exists():
            print(f"{RED}Error: JSON results file not found at '{json_file}'.{RESET}")
            return 1
        try:
            content = json_file.read_text(encoding="utf-8")
            data = json.loads(content)
            scan_result = ScanResult.from_dict(data)
        except Exception as e:
            print(f"{RED}Error: Failed to rehydrate ScanResult from '{json_file}': {str(e)}{RESET}")
            return 1

        from skillpulse.reporter import HTMLReporter
        HTMLReporter.generate(scan_result, out_path)
        print_banner()
        print(f"  {GREEN}[OK] Visual report rehydrated from JSON:{RESET} {CYAN}{json_file}{RESET}")
        print(f"  {GREEN}[OK] HTML report generated:{RESET} {CYAN}{out_path}{RESET}\n")
        return 0

    # Fallback to scanning current directory
    print_banner()
    workspace_root = Path.cwd()
    skill_files = SkillScanner.find_skills(workspace_root)
    skill_reports = [SkillLinter.lint_file(p) for p in skill_files]

    mcp_path = MCPConfigDiscovery.find_mcp_config(workspace_root)
    mcp_report = None
    if mcp_path and mcp_path.exists():
        mcp_report = MCPContractValidator.validate_file(mcp_path, skill_reports)

    from skillpulse.reporter import HTMLReporter
    scan_result = HealthScorer.score_scan(
        skill_reports, mcp_report, str(workspace_root), datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    HTMLReporter.generate(scan_result, out_path)
    print(f"  {GREEN}[OK] Visual diagnostic report generated:{RESET} {CYAN}{out_path}{RESET}\n")
    return 0


def cmd_fix(args: argparse.Namespace) -> int:
    """Executes deterministic contract and schema auto-fixer."""
    from skillpulse.fixer import WorkspaceFixer

    fmt = getattr(args, "format", "text")
    if fmt == "text":
        print_banner()

    workspace_root = Path(getattr(args, "path", ".")).resolve()
    skills_dir = Path(args.skills_dir).resolve() if getattr(args, "skills_dir", None) else None
    mcp_config = Path(args.mcp_config).resolve() if getattr(args, "mcp_config", None) else None
    dry_run = getattr(args, "dry_run", False)
    output_dir = Path(args.output_dir).resolve() if getattr(args, "output_dir", None) else None

    fixer = WorkspaceFixer(
        workspace_root=workspace_root,
        skills_dir=skills_dir,
        mcp_config_path=mcp_config,
        dry_run=dry_run,
        output_dir=output_dir,
    )

    fix_result = fixer.fix()

    if fmt == "json":
        res_data = {
            "workspace_path": fix_result.workspace_path,
            "dry_run": fix_result.dry_run,
            "total_actions": fix_result.total_actions,
            "actions": [
                {
                    "rule_id": a.rule_id,
                    "target_file": a.target_file,
                    "description": a.description,
                    "applied": a.applied,
                    "diff_summary": a.diff_summary,
                }
                for a in fix_result.actions
            ],
            "pre_score": fix_result.pre_scan.health_score if fix_result.pre_scan else None,
            "post_score": fix_result.post_scan.health_score if fix_result.post_scan else None,
        }
        print(json.dumps(res_data, indent=2))
        return 0

    mode_label = f"{YELLOW}[DRY-RUN - No files modified]{RESET}" if dry_run else f"{GREEN}[APPLIED]{RESET}"
    print(f"{BOLD}=== SkillPulse Workspace Fixer ==={RESET} {mode_label}\n")
    print(f"  {GRAY}Target Workspace: {fix_result.workspace_path}{RESET}")
    if output_dir:
        print(f"  {CYAN}Output Directory: {output_dir}{RESET}")

    pre_s = fix_result.pre_scan.health_score if fix_result.pre_scan else 0
    pre_g = fix_result.pre_scan.grade if fix_result.pre_scan else "F"
    post_s = fix_result.post_scan.health_score if fix_result.post_scan else pre_s
    post_g = fix_result.post_scan.grade if fix_result.post_scan else pre_g

    print(f"  Initial Score: {BOLD}{pre_s}% (Grade {pre_g}){RESET}")
    print(f"  Remediations Proposed/Applied: {BOLD}{len(fix_result.actions)}{RESET}\n")

    if not fix_result.actions:
        print(f"  {GREEN}No automated fixable defects detected. Workspace is clean or requires manual review.{RESET}\n")
    else:
        for idx, act in enumerate(fix_result.actions, start=1):
            status = f"{GREEN}[FIXED]{RESET}" if act.applied else f"{YELLOW}[PROPOSED]{RESET}"
            print(f"  {status} {BOLD}{act.rule_id}{RESET}: {act.description}")
            print(f"    {GRAY}File: {act.target_file}{RESET}")
            if act.diff_summary:
                print(f"    {CYAN}Detail: {act.diff_summary}{RESET}")
            print()

        print(f"  {BOLD}Score Progression:{RESET} {pre_s}% ({pre_g}) -> {BOLD}{post_s}% ({post_g}){RESET}")
        if dry_run:
            print(f"  {GRAY}Run without --dry-run (or pass --output-dir <path>) to write changes.{RESET}\n")
        else:
            print(f"  {GREEN}Remediations written to disk.{RESET}\n")

    return 0


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skillpulse",
        description="Linter, test harness, and diagnostics for Agent Skills & MCP (2025-11-25) schemas."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # lint-skills
    p_lint = subparsers.add_parser("lint-skills", help="Lint Agent Skills (SKILL.md)")
    p_lint.add_argument("path", nargs="?", default=".", help="Directory or file path to lint")
    p_lint.add_argument("--format", choices=["text", "json", "markdown"], default="text", help="Output format (default: text)")
    p_lint.add_argument("--json-output", default=None, help="Save machine-readable JSON results to specified file")

    # test-mcp
    p_mcp = subparsers.add_parser("test-mcp", help="Validate MCP tool schemas and contracts")
    p_mcp.add_argument("config", nargs="?", default="mcp_tools.json", help="Path to MCP tools JSON file")
    p_mcp.add_argument("--skills-dir", default=None, help="Specific skills directory to cross-check contracts")
    p_mcp.add_argument("--format", choices=["text", "json", "markdown"], default="text", help="Output format (default: text)")
    p_mcp.add_argument("--json-output", default=None, help="Save machine-readable JSON results to specified file")

    # scan
    p_scan = subparsers.add_parser("scan", help="Run full scan (Skills + MCP)")
    p_scan.add_argument("path", nargs="?", default=".", help="Target workspace path")
    p_scan.add_argument("--skills-dir", default=None, help="Specific skills directory")
    p_scan.add_argument("--mcp-config", default=None, help="Specific MCP tools JSON file")
    p_scan.add_argument("--report", default="skillpulse-report.html", help="Path for HTML report output")
    p_scan.add_argument("--format", choices=["text", "json", "markdown"], default="text", help="Output format (default: text)")
    p_scan.add_argument("--json-output", default=None, help="Save machine-readable JSON results to specified file")

    # report
    p_rep = subparsers.add_parser("report", help="Generate HTML report from scan results")
    p_rep.add_argument("input", nargs="?", default=None, help="Input results JSON file (optional)")
    p_rep.add_argument("--from-json", default=None, help="Path to saved JSON scan results to rehydrate into HTML")
    p_rep.add_argument("--output", default="skillpulse-report.html", help="HTML report output path")

    # fix
    p_fix = subparsers.add_parser("fix", help="Deterministically remediate common skill and MCP contract defects")
    p_fix.add_argument("path", nargs="?", default=".", help="Workspace path to fix")
    p_fix.add_argument("--skills-dir", default=None, help="Specific skills directory to fix")
    p_fix.add_argument("--mcp-config", default=None, help="Specific MCP tools JSON file to fix")
    p_fix.add_argument("--dry-run", action="store_true", default=False, help="Simulate fixes without modifying disk")
    p_fix.add_argument("--output-dir", default=None, help="Clone workspace and apply fixes in target directory")
    p_fix.add_argument("--format", choices=["text", "json"], default="text", help="Output format (default: text)")

    return parser


def main(argv: List[str] = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command or args.command == "scan":
        if not hasattr(args, "path"):
            args.path = "."
        if not hasattr(args, "skills_dir"):
            args.skills_dir = None
        if not hasattr(args, "mcp_config"):
            args.mcp_config = None
        if not hasattr(args, "report"):
            args.report = "skillpulse-report.html"
        if not hasattr(args, "format"):
            args.format = "text"
        if not hasattr(args, "json_output"):
            args.json_output = None
        return cmd_scan(args)
    elif args.command == "lint-skills":
        return cmd_lint_skills(args)
    elif args.command == "test-mcp":
        return cmd_test_mcp(args)
    elif args.command == "report":
        return cmd_report(args)
    elif args.command == "fix":
        return cmd_fix(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
