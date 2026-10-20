---
doc: spec
status: approved
---

# skillpulse — Technical Specification

## How This Works, In Plain Language
`skillpulse` is a developer tool and test harness that inspects AI agent configurations. When you run `skillpulse scan`, it immediately does two things:
1. It walks your project tree finding every `SKILL.md` file (the standard format used by Claude Code, Antigravity, and other agents). It parses the header metadata (YAML frontmatter) and checks whether the required keys exist, whether prompt instructions have clear triggers, and whether the prompt is within safe token limits.
2. It discovers Model Context Protocol (MCP) tool declarations (e.g. `mcp_tools.json` or MCP manifests). It validates each tool against the official `2025-11-25` schema standard, checks parameter definitions (`inputSchema`), and performs contract cross-checking against scanned `SKILL.md` files to catch Ghost Tools (tools called in prompts that do not exist in MCP) and Undocumented / Orphan MCP tools.

All results are scored into a 0–100 Ecosystem Health Score. You get instant colored feedback in your terminal and an interactive, standalone HTML report file (`skillpulse-report.html`) you can double-click to view in any web browser without needing any server or internet connection.

## The Core Journey Through the System
Implements `prd.md > The Core Journey`.

1. **User Invokes CLI:** `skillpulse scan` is entered in terminal.
2. **Path Discovery:** `cli.py` invokes `linter.SkillScanner` and `mcp_tester.MCPConfigDiscovery`.
3. **Skill Parsing:** `linter.SkillLinter.lint_file(path)` extracts frontmatter delimiters (`---`), parses YAML properties, executes validation rules (`SKILL001`–`SKILL006`), and computes token load estimates.
4. **MCP Contract & Schema Validation:** `mcp_tester.MCPContractValidator.validate(tools_data, skills)` parses the JSON tool schemas, verifies `MCP001` (spec format) and `MCP002` (schema completeness), and cross-checks referenced tools in `skills` for `MCP003` (ghost tools) and `MCP004` (undocumented/orphan tools).
5. **Health Calculation:** `scorer.HealthScorer.calculate(results)` tallies issues, computes penalties, and derives the composite score and letter grade.
6. **Output Delivery:** `cli.py` prints ANSI diagnostic tables to stdout and calls `reporter.HTMLReporter.generate(results, "skillpulse-report.html")`.

## Stack
- **Language:** Python 3.10+ (tested with Python 3.13)
- **Standard Library Components:**
  - `json`: JSON-RPC / MCP tool schema parsing and schema structure validation.
  - `pathlib`: Cross-platform filesystem traversal and path resolution.
  - `re`: Regular expression matching for frontmatter delimiters, keyword triggers, and tool references.
  - `dataclasses`: Type-safe structured data models for reports and diagnostics.
  - `argparse`: Command-line interface and subcommand handling.
- **Testing:** `pytest` (high-speed automated unit and integration tests).
- **Rationale & Tradeoffs:** Utilizing Python standard library primitives ensures instantaneous installation with zero heavyweight binary wheel compilation (e.g. no C-compiler or Rust toolchain required on Windows).

## Where It Runs and How Someone Tries It
- **Runtime:** Local developer workstation or CI container running Python 3.10+.
- **Start Command:**
  ```powershell
  python -m skillpulse scan
  # or test specific MCP tool schemas:
  python -m skillpulse test-mcp examples/sample_mcp_tools.json
  ```
- **Interactive Report:** Double-click or run `start skillpulse-report.html` to open the visual dashboard in your default web browser.
- **Automated Tests:**
  ```powershell
  python -m pytest tests/ -v
  ```
- **Demo Recording Instructions:**
  1. Open terminal in `skillpulse`.
  2. Run `python -m skillpulse scan` demonstrating live terminal diagnostics.
  3. Open `skillpulse-report.html` showcasing the interactive visual health dashboard.

## Look and Feel
Carried forward from `prd.md > Look and Feel`:
- **Palette:** Obsidian canvas (`#090d16`), deep navy surfaces (`#121826`), electric cyan (`#06b6d4`), emerald green (`#10b981`), amber warning (`#f59e0b`), rose error (`#ef4444`).
- **Typography:** Modern sans-serif headings with high-contrast monospace code blocks (`SFMono-Regular`, `Consolas`, `monospace`).
- **Density:** Crisp, information-dense, high-utility developer tool aesthetics with clear visual hierarchy.

## Components

### 1. SkillPulseCLI (`skillpulse/cli.py`)
- Implements `prd.md > Unified CLI Interface`.
- Parses subcommands: `scan`, `lint-skills`, `test-mcp`, `report`.
- Outputs formatted ANSI terminal output, error summaries, and handles POSIX exit codes (0 = success/warnings, 1 = critical errors).

### 2. SkillScanner & SkillLinter (`skillpulse/linter.py`)
- Implements `prd.md > Agent Skill Static Linter`.
- Discovers `SKILL.md` files recursively in specified directories.
- Extracts frontmatter between `---` markers.
- Evaluates rules `SKILL001` through `SKILL006` (including frontmatter schema, token budgets, and local relative markdown links).
- Provides heuristic token budget calculation (~1.3 tokens per word).

### 3. MCPContractValidator (`skillpulse/mcp_tester.py`)
- Implements `prd.md > MCP 2025-11-25 Contract & Schema Validator`.
- Validates MCP tool definition schemas against `2025-11-25` standards (`MCP001`, `MCP002`).
- Cross-references tools called or referenced in `SKILL.md` files against defined tools to flag Ghost Tools (`MCP003`).
- Identifies orphaned/undocumented MCP tools (`MCP004`).
- Runs deterministically in <10ms with zero subprocess deadlock or pipe hang risk.

### 4. HealthScorer (`skillpulse/scorer.py`)
- Implements `prd.md > Ecosystem Health Scoring`.
- Implements deterministic scoring formula:
  $$\text{Score} = \max(0, 100 - (20 \times \text{total\_errors}) - (5 \times \text{total\_warnings}))$$
- Assigns letter grades: A (90–100), B (80–89), C (70–79), D (60–69), F (<60).

### 5. HTMLReporter (`skillpulse/reporter.py`)
- Implements `prd.md > Self-Contained HTML Report Generator`.
- Emits a standalone, zero-dependency HTML file containing CSS styles, SVG charts, and interactive filtering JavaScript.

## Data Model
- **`DiagnosticIssue`:**
  - `rule_id: str` (e.g. `SKILL001`, `MCP001`)
  - `severity: str` (`ERROR`, `WARNING`, `INFO`)
  - `message: str`
  - `line_number: Optional[int]`
  - `suggestion: str`
- **`SkillReport`:**
  - `file_path: str`
  - `name: str`
  - `description: str`
  - `is_valid: bool`
  - `token_count: int`
  - `referenced_tools: List[str]`
  - `issues: List[DiagnosticIssue]`
- **`MCPTool`:**
  - `name: str`
  - `description: str`
  - `input_schema: dict`
- **`MCPReport`:**
  - `source_file: str`
  - `protocol_version: str`
  - `tools: List[MCPTool]`
  - `ghost_tools: List[str]`
  - `orphan_tools: List[str]`
  - `issues: List[DiagnosticIssue]`
- **`ScanResult`:**
  - `timestamp: str`
  - `workspace_path: str`
  - `health_score: int`
  - `grade: str`
  - `skills: List[SkillReport]`
  - `mcp_report: Optional[MCPReport]`

## File Structure
```
skillpulse/
├── devpost/                  # Hackathon planning workspace
│   ├── learner-profile.md
│   ├── scope.md
│   ├── scope.html
│   ├── prd.md
│   ├── prd.html
│   ├── spec.md
│   └── spec.html
├── skillpulse/               # Main Python package
│   ├── __init__.py
│   ├── __main__.py           # python -m skillpulse entry point
│   ├── cli.py                # CLI runner & argument parsing
│   ├── models.py             # Data classes (ScanResult, DiagnosticIssue, etc.)
│   ├── linter.py             # SKILL.md static parser & rule evaluator
│   ├── mcp_tester.py         # MCP 2025-11-25 contract & schema validator
│   ├── scorer.py             # Health score & grading engine
│   └── reporter.py           # Self-contained HTML report compiler
├── tests/                    # Pytest test suite
│   ├── test_linter.py        # Valid & invalid SKILL.md unit tests
│   ├── test_mcp_tester.py    # MCP schema & ghost tool contract tests
│   ├── test_scorer.py        # Health score calculation unit tests
│   └── test_cli.py           # End-to-end CLI command tests
├── examples/                 # Sample skills and MCP config for demo
│   ├── healthy_workspace/    # Reference 100% Grade A workspace (0 errors, 0 warnings)
│   │   ├── skills/
│   │   │   ├── opportunity-scout/SKILL.md
│   │   │   └── rule-auditor/SKILL.md
│   │   └── mcp_tools.json
│   ├── broken_workspace/     # Broken demo workspace (ghost & orphan tools, schema error)
│   │   ├── skills/broken-skill/SKILL.md
│   │   └── mcp_tools.json
│   └── sample_mcp_tools.json # Legacy reference MCP 2025-11-25 tool definitions
├── .gitignore
├── LICENSE                   # MIT License
├── pyproject.toml            # Python packaging metadata & entrypoint
├── README.md                 # Project documentation & quickstart
├── scope.md                  # Root copy of approved scope
├── prd.md                    # Root copy of approved PRD
└── spec.md                   # Root copy of approved Technical Spec
```

## External Services and Dependencies
- **External Services:** None. 100% local, air-gap compatible, zero telemetry.
- **Python Dependencies:** Standard Library (`json`, `pathlib`, `re`, `argparse`, `dataclasses`).
- **Development Dependencies:** `pytest` (for test suite).

## Important Failure Modes
1. **Malformed YAML Frontmatter:** Handled by `linter.py` using robust regex fallback line-by-line parsing to extract keys even when standard YAML syntax is partially broken, reporting exact error line without crashing.
2. **Missing or Malformed MCP Tool Schema:** Handled by `mcp_tester.py` checking required fields (`name`, `description`, `inputSchema`) and logging structured `MCP002` issues without raising uncaught exceptions.
3. **Ghost Tools in Skills:** Handled by cross-checking extracted tool references against the MCP tool catalog, surfacing `MCP003` error issues with remediation suggestions.

## What Was Simplified and Why
- **Deterministic Schema & Contract Validation vs. Stdio Subprocess:** In-process validation eliminates child process hanging, OS pipe deadlocks, and subprocess timeouts while ensuring 100% cross-platform reliability on Windows and Linux in <10ms.
- **Word-based Heuristic Token Estimation vs. tiktoken Binary:** Heuristic estimation (~1.3 tokens per word) eliminates large binary wheel dependencies and C-compiler requirements on Windows while delivering ~95% estimation accuracy.

## Decisions and Open Issues
- **Tool Reference Extraction:** `linter.py` extracts tool mentions only from explicit frontmatter lists (`mcp_tools`, `tools`) or backticked identifiers in markdown sections containing "MCP" or "Tools" in their heading, deliberately excluding sibling skill names (`1-start`, `2-scope`, etc.) to prevent false positives.
- **No Open Issues:** The technical specification is complete, sized appropriately for the proof of concept, and ready for immediate implementation in `5-build`.
