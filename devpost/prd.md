---
doc: prd
status: approved
---

# skillpulse — Product Requirements

An open-source developer linter, test harness, and diagnostic report generator for AI Agent Skills (`SKILL.md`) and Model Context Protocol (`MCP` 2025-11-25) schemas and contracts.

Source: `scope.md > The Unique Kernel` and `scope.md > The POC Boundary`.

## The Core Journey
1. **Invocation:** The developer runs `skillpulse scan` in their project directory (or targets specific paths via `skillpulse scan --skills-dir .agents/skills --mcp-config mcp_tools.json`).
2. **Skill Discovery & Static Parsing:** The engine scans the workspace for `SKILL.md` files, parses YAML frontmatter delimiters, extracts metadata (`name`, `description`, tags), and checks markdown body structure.
3. **Skill Rule Evaluation:** Linter rules run against each skill, evaluating YAML syntax, required attributes, prompt instruction formatting, and token budget estimation (~1.3 tokens per word).
4. **MCP Schema & Contract Ingestion:** The engine reads MCP tool definitions (`mcp_tools.json` or MCP manifests), validates them against the MCP 2025-11-25 tool schema standard, and cross-checks tool names and signatures referenced in `SKILL.md` prompt instructions against the defined MCP tools.
5. **Contract Cross-Checking:** Detects Ghost Tools (tools called in prompt instructions but missing from MCP tool declarations), Missing Schema Fields, and Undocumented / Orphaned Tools.
6. **Health Score Calculation:** All findings are aggregated into a deterministic 0–100 Ecosystem Health Score with letter grade classification.
7. **Report Delivery:** Diagnostic output is streamed to stdout in a color-coded table, and a self-contained, interactive HTML dashboard (`skillpulse-report.html`) is compiled and saved.

## Screens and Layout
### Surface 1: Terminal CLI (ANSI Stdio)
- Command-line interface featuring colored status glyphs (`✓` green pass, `⚠` yellow warn, `✖` red error).
- Tabular breakdown of each discovered Skill and MCP tool contract.
- Executive summary displaying overall Health Score, error tallies, and path to the generated HTML report.

### Surface 2: Visual HTML Diagnostic Dashboard (`skillpulse-report.html`)
- **Header & Metric Cards:** Overall Health Score radial gauge, total skills scanned, active MCP tools verified, critical issue count.
- **Skill Inspector Panel:** Interactive cards for each scanned skill showing file path, frontmatter validity badge, estimated token consumption bar, and expandable linting diagnostics with remediation hints.
- **MCP Contract Inspector Panel:** Tool schema compliance status, verified protocol version (`2025-11-25`), cross-contract link badges, and structured parameter schema inspectors.
- **Interactive Filter Toolbar:** 1-click toggles to filter issues by severity (All, Critical Errors, Warnings, Optimization Tips).

## Look and Feel
- **Theme:** Obsidian dark mode (`#090d16` canvas, `#131b2e` card surfaces).
- **Accents:** Electric cyan (`#06b6d4`) for navigation and branding, vibrant emerald (`#10b981`) for passing checks, amber (`#f59e0b`) for warnings, and rose (`#f43f5e`) for critical schema violations.
- **Typography:** Modern clean sans-serif for UI labels paired with crisp monospace (`Fira Code`, `SF Mono`, `Consolas`) for code snippets and JSON-RPC payloads.
- **Interactions:** Subtle CSS micro-transitions, hover glows, and collapsible issue disclosure widgets.

## Features and Behavior

### 1. Agent Skill Static Linter
- Implements `scope.md > The POC Boundary > Static linter for SKILL.md`.
- **Behavior:** Scans and validates any markdown file following the Agent Skills specification.
- **Rules Evaluated:**
  - `SKILL001`: Valid YAML frontmatter enclosed by `---`.
  - `SKILL002`: Required `name` attribute present (1–64 characters, lowercase alphanumeric and hyphens).
  - `SKILL003`: Required `description` attribute present (descriptive, action-oriented).
  - `SKILL004`: Recommended trigger phrase or activation cues present.
  - `SKILL005`: Token budget warning if body exceeds 2,500 estimated tokens.
- **Acceptance Criteria:**
  - [x] Correctly identifies valid vs. malformed YAML frontmatter.
  - [x] Emits error if `name` or `description` is missing or invalid.
  - [x] Accurately estimates token usage within 10% of standard BPE tokenizers.

### 2. MCP 2025-11-25 Contract & Schema Validator
- Implements `scope.md > The POC Boundary > MCP Server Test Harness`.
- **Behavior:** Parses MCP tool declarations, verifies compliance with the `2025-11-25` tool specification, and cross-checks declared tools against prompt instructions in skills.
- **Rules Evaluated:**
  - `MCP001`: Valid MCP `2025-11-25` tool specification format (array of tool definitions).
  - `MCP002`: Tool Schema Completeness: each tool requires non-empty `name`, `description`, and valid `inputSchema` (`type: "object"`, `properties` object).
  - `MCP003`: Ghost Tool Detection: flags tool references in `SKILL.md` that are not declared in the MCP tools manifest.
  - `MCP004`: Undocumented / Orphan MCP Tool Warning: flags declared MCP tools that have no description or are never referenced across skills.
- **Acceptance Criteria:**
  - [x] Successfully validates standard compliant MCP 2025-11-25 tool schemas.
  - [x] Flags missing `inputSchema`, invalid types, or missing properties.
  - [x] Detects ghost tool calls in skills and orphaned MCP tools.
  - [x] Runs deterministically in <10ms without child process deadlock risk.

### 3. Ecosystem Health Scoring
- Implements `scope.md > The Unique Kernel`.
- **Behavior:** Calculates a deterministic health score from 0 to 100:
  $$\text{Score} = \max(0, 100 - (25 \times \text{Errors}) - (10 \times \text{Warnings}) - (2 \times \text{Info}))$$
- **Letter Grades:** 90–100: Grade A (Excellent), 80–89: Grade B (Good), 70–79: Grade C (Needs Improvement), <70: Grade F (Failing).
- **Acceptance Criteria:**
  - [x] Clean run with no issues scores 100 (Grade A).
  - [x] Flawed run reflects exact weighted penalty deductions.

### 4. Self-Contained HTML Report Generator
- Implements `scope.md > What "Working" Looks Like`.
- **Behavior:** Compiles all scan findings into an offline, single-file HTML document with embedded CSS and zero external JavaScript libraries.
- **Acceptance Criteria:**
  - [x] Generated file opens seamlessly in any modern browser without web server requirement.
  - [x] Provides functional client-side filtering for error severities.

### 5. Unified CLI Interface
- Implements `scope.md > The Core Loop`.
- **Commands:**
  - `skillpulse scan [PATH]`: Runs comprehensive scan on both skills and MCP configs.
  - `skillpulse lint-skills [DIR]`: Runs only the skill linter.
  - `skillpulse test-mcp [CONFIG]`: Runs only the MCP contract & schema validator.
  - `skillpulse report [JSON_PATH]`: Converts saved JSON results into visual HTML.
- **Acceptance Criteria:**
  - [x] Returns standard POSIX exit code 0 on clean runs, code 1 when critical errors exist (CI/CD compatible).

## States and Boundaries
- **Empty State (No Skills / Configs Found):** Displays friendly message guiding the user to specify a directory or initialize sample skills.
- **Perfect Passing State:** Displays vibrant emerald badge, 100/100 Grade A score, and congratulatory summary.
- **Warning-Only State:** Displays amber indicators with actionable optimization suggestions, exit code remains 0.
- **Error State:** Displays high-contrast red error badges with line numbers, error descriptions, and exit code 1.

## Product Decisions
- **Deterministic In-Process Schema & Contract Checking:** Selected over spawning child subprocesses with stdio pipes to eliminate cross-platform hanging pipes, shell escaping bugs, and process deadlock risks on Windows/Linux while providing instant sub-millisecond execution.
- **Single-File Zero-Dependency HTML:** Selected over external React/Vite dashboard bundle to ensure instant generation, 100% offline reliability, and zero build tool prerequisites.
- **Python 3 Standard Library First:** Uses standard Python library modules (`json`, `pathlib`, `re`, `argparse`, `dataclasses`) with minimal lightweight dependencies for maximum portability.

## What We're Building
A robust, high-performance CLI utility and interactive HTML report generator covering all features listed in Section 4.

## Deferred From the POC
- **GitHub Actions Custom Action (`skillpulse-action`):** Deferred to post-PoC release to keep initial hackathon focus on the core CLI engine.
- **SSE/WebSocket Remote MCP Transport:** Deferred to future minor version.
- **Automatic Code Fixer (`skillpulse fix`):** Deferred; PoC outputs explicit copy-pasteable remediation diffs.

## Non-Goals
- Will not execute untrusted agent skill code or arbitrary model inferences.
- Will not store any credentials, API keys, or remote telemetry.
- Will not require a background daemon or cloud server to function.

## Open Questions
- None. The scope, interfaces, and behaviors are fully defined and validated.
