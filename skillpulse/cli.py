"""
Command-line interface and terminal renderer for skillpulse.
"""

import argparse
from datetime import datetime
import sys
from pathlib import Path
from typing import List, Optional

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
    color = GREEN if scan.health_score >= 90 else (CYAN if scan.health_score >= 80 else (YELLOW if scan.health_score >= 70 else RED))

    print(f"{BOLD}===================================================={RESET}")
    print(f"  {BOLD}Ecosystem Health Score:{RESET} {color}{BOLD}{scan.health_score}%{RESET} ({scan.grade})")
    print(f"  {GRAY}{HealthScorer.grade_description(scan.grade, scan.total_errors)}{RESET}")
    print(f"  {BOLD}Total Critical Errors:{RESET} {RED if scan.total_errors else GREEN}{scan.total_errors}{RESET}")
    print(f"  {BOLD}Total Warnings:{RESET} {YELLOW if scan.total_warnings else GREEN}{scan.total_warnings}{RESET}")
    print(f"{BOLD}===================================================={RESET}\n")


def cmd_lint_skills(args: argparse.Namespace) -> int:
    """Executes skill linter only."""
    print_banner()
    target_path = Path(args.path).resolve()
    skill_files = SkillScanner.find_skills(target_path)
    reports = [SkillLinter.lint_file(p) for p in skill_files]
    errors = render_skill_reports(reports)
    return 1 if errors > 0 else 0


def cmd_test_mcp(args: argparse.Namespace) -> int:
    """Executes MCP tool schema and contract validation."""
    print_banner()
    config_path = Path(args.config).resolve()

    if not config_path.exists():
        discovered = MCPConfigDiscovery.find_mcp_config(Path.cwd())
        if discovered:
            config_path = discovered
        else:
            print(f"{RED}Error: MCP config not found at '{args.config}' and none discovered in workspace.{RESET}")
            return 1

    skill_files = SkillScanner.find_skills(Path.cwd())
    scanned_skills = [SkillLinter.lint_file(p) for p in skill_files]

    report = MCPContractValidator.validate_file(config_path, scanned_skills)
    errors = render_mcp_report(report)
    return 1 if errors > 0 else 0


def cmd_scan(args: argparse.Namespace) -> int:
    """Executes full unified scan (Skills + MCP) and prints health score."""
    print_banner()
    workspace_root = Path(args.path).resolve()

    # 1. Discover and lint skills
    skills_dir = Path(args.skills_dir).resolve() if args.skills_dir else workspace_root
    skill_files = SkillScanner.find_skills(skills_dir)
    skill_reports = [SkillLinter.lint_file(p) for p in skill_files]
    render_skill_reports(skill_reports)

    # 2. Discover and validate MCP config
    mcp_report: Optional[MCPReport] = None
    if args.mcp_config:
        mcp_path = Path(args.mcp_config).resolve()
    else:
        mcp_path = MCPConfigDiscovery.find_mcp_config(workspace_root)

    if mcp_path and mcp_path.exists():
        mcp_report = MCPContractValidator.validate_file(mcp_path, skill_reports)
        render_mcp_report(mcp_report)
    else:
        print(f"{BOLD}=== Model Context Protocol (MCP) ==={RESET}\n")
        print(f"  {YELLOW}No MCP tool definition file (mcp_tools.json) found.{RESET}\n")

    # 3. Calculate health score
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scan_result = HealthScorer.score_scan(skill_reports, mcp_report, str(workspace_root), timestamp)
    render_scan_summary(scan_result)

    # 4. Generate HTML report if reporter is available
    report_path = Path(args.report).resolve()
    try:
        from skillpulse.reporter import HTMLReporter
        HTMLReporter.generate(scan_result, report_path)
        print(f"  {GREEN}[OK] Visual diagnostic report generated:{RESET} {CYAN}{report_path}{RESET}\n")
    except ImportError:
        pass

    return 1 if scan_result.total_errors > 0 else 0


def cmd_report(args: argparse.Namespace) -> int:
    """Generates visual HTML report from full scan or specific inputs."""
    print_banner()
    workspace_root = Path.cwd()
    skill_files = SkillScanner.find_skills(workspace_root)
    skill_reports = [SkillLinter.lint_file(p) for p in skill_files]

    mcp_path = MCPConfigDiscovery.find_mcp_config(workspace_root)
    mcp_report = None
    if mcp_path and mcp_path.exists():
        mcp_report = MCPContractValidator.validate_file(mcp_path, skill_reports)

    from skillpulse.reporter import HTMLReporter
    scan_result = HealthScorer.score_scan(skill_reports, mcp_report, str(workspace_root), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    out_path = Path(args.output).resolve()
    HTMLReporter.generate(scan_result, out_path)
    print(f"  {GREEN}[OK] Visual diagnostic report generated:{RESET} {CYAN}{out_path}{RESET}\n")
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

    # test-mcp
    p_mcp = subparsers.add_parser("test-mcp", help="Validate MCP tool schemas and contracts")
    p_mcp.add_argument("config", nargs="?", default="mcp_tools.json", help="Path to MCP tools JSON file")

    # scan
    p_scan = subparsers.add_parser("scan", help="Run full scan (Skills + MCP)")
    p_scan.add_argument("path", nargs="?", default=".", help="Target workspace path")
    p_scan.add_argument("--skills-dir", default=None, help="Specific skills directory")
    p_scan.add_argument("--mcp-config", default=None, help="Specific MCP tools JSON file")
    p_scan.add_argument("--report", default="skillpulse-report.html", help="Path for HTML report output")

    # report
    p_rep = subparsers.add_parser("report", help="Generate HTML report from scan results")
    p_rep.add_argument("input", nargs="?", default=None, help="Input results JSON file (optional)")
    p_rep.add_argument("--output", default="skillpulse-report.html", help="HTML report output path")

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
        return cmd_scan(args)
    elif args.command == "lint-skills":
        return cmd_lint_skills(args)
    elif args.command == "test-mcp":
        return cmd_test_mcp(args)
    elif args.command == "report":
        return cmd_report(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
