---
doc: checklist
status: approved
---

# Build Checklist

Build mode: fast

## Slices

- [x] **1. Agent Skill Static Linter & Token Estimator**
  Becomes usable: `python -m skillpulse lint-skills <path>` discovers `SKILL.md` files, parses frontmatter delimiters, checks rules `SKILL001`–`SKILL005`, estimates token budget, and outputs structured CLI diagnostics.
  Why now: Proves the whole path end to end on the first slice — package scaffolding, models, frontmatter parsing, AST/regex analysis, and terminal output.
  PRD ref: `prd.md > Features and Behavior > 1. Agent Skill Static Linter`
  Spec ref: `spec.md > Components > 2. SkillScanner & SkillLinter`, `spec.md > Data Model`
  Build: Scaffold `pyproject.toml`, `skillpulse/__init__.py`, `skillpulse/models.py`, `skillpulse/linter.py`, and basic CLI runner in `skillpulse/cli.py` & `skillpulse/__main__.py`. Include unit tests in `tests/test_linter.py`.
  Verify (mechanical): Run `python -m pytest tests/test_linter.py -v` and run `python -m skillpulse lint-skills .agents/skills`.
  Learner check: Run `python -m skillpulse lint-skills .agents/skills` and see all 6 skills detected and linted with token load indicators.
  Commit: `feat(linter): implement agent skill static linter and token estimator`

- [x] **2. MCP 2025-11-25 Contract & Schema Validator**
  Becomes usable: `python -m skillpulse test-mcp <path>` validates MCP tool declarations against `2025-11-25` schema rules (`MCP001`, `MCP002`), cross-checks referenced tools in `SKILL.md` to catch Ghost Tools (`MCP003`), and detects orphaned MCP tools (`MCP004`).
  Why now: Brings in the other half of the dual-ecosystem kernel, proving cross-contract validation between prompt skills and MCP schemas in sub-millisecond execution.
  PRD ref: `prd.md > Features and Behavior > 2. MCP 2025-11-25 Contract & Schema Validator`
  Spec ref: `spec.md > Components > 3. MCPContractValidator`
  Build: Implement `skillpulse/mcp_tester.py`, wire subcommand `test-mcp` into `cli.py`, add `examples/sample_mcp_tools.json` and unit tests in `tests/test_mcp_tester.py`.
  Verify (mechanical): Run `python -m pytest tests/test_mcp_tester.py -v` and run `python -m skillpulse test-mcp examples/sample_mcp_tools.json`.
  Learner check: Run `python -m skillpulse test-mcp examples/sample_mcp_tools.json` and verify compliant tool schemas pass while ghost tools in test fixtures are accurately flagged.
  Commit: `feat(mcp): implement deterministic MCP 2025-11-25 schema and ghost tool contract validator`

- [ ] **3. Ecosystem Health Scorer & Unified CLI Scan**
  Becomes usable: `python -m skillpulse scan` executes combined scanning of both skills and MCP tools in a single command, computing the deterministic 0–100 Ecosystem Health Score, letter grade (A/B/C/F), ANSI summary table, and returning standard CI exit codes.
  Why now: Synthesizes both subsystems into the unified developer workflow and enables CI/CD automation.
  PRD ref: `prd.md > Features and Behavior > 3. Ecosystem Health Scoring`, `prd.md > Unified CLI Interface`
  Spec ref: `spec.md > Components > 1. SkillPulseCLI`, `spec.md > Components > 4. HealthScorer`
  Build: Implement `skillpulse/scorer.py`, complete `skillpulse/cli.py` scan workflow, add `tests/test_scorer.py` and `tests/test_cli.py`.
  Verify (mechanical): Run `python -m pytest tests/ -v` and run `python -m skillpulse scan`.
  Learner check: Run `python -m skillpulse scan` in the workspace and verify health score and ANSI diagnostic table.
  Commit: `feat(scorer): implement ecosystem health score engine and unified scan CLI`

- [ ] **4. Self-Contained Interactive HTML Report Generator**
  Becomes usable: `skillpulse scan` auto-generates `skillpulse-report.html` (or `python -m skillpulse report`), providing an offline-ready, high-polish visual diagnostic dashboard with score gauge, tool schemas, and copyable remediation diffs.
  Why now: Completes the full end-to-end product journey and delivers the demo-ready visual deliverable.
  PRD ref: `prd.md > Features and Behavior > 4. Self-Contained HTML Report Generator`, `prd.md > Screens and Layout > Surface 2`
  Spec ref: `spec.md > Components > 5. HTMLReporter`
  Build: Implement `skillpulse/reporter.py`, connect report compilation into `skillpulse/cli.py`, add sample test cases for reporter.
  Verify (mechanical): Run `python -m skillpulse scan` and verify `skillpulse-report.html` is generated, valid HTML5, and opens with full offline CSS/JS.
  Learner check: Open `skillpulse-report.html` in browser, test severity filter buttons and collapsible cards.
  Commit: `feat(reporter): implement self-contained interactive visual HTML dashboard generator`

## Hands-on Checkpoints

- [x] Early usable behavior explored — Slice 2 boundary (Skill Linter + MCP Cross-Contract Validator working)
- [ ] Final kick-the-tires exploration and feedback completed

## Final Review

- [ ] Final review complete — feedback resolved and learner confirms ready to ship

## Code Tour and App Map

- [ ] Learning activity complete — guided route, focused alternative, prior practice connected, or brief recap
- [ ] Optional edit and transfer reflection addressed — offered/declined/already covered/not applicable as appropriate
- [ ] `devpost/app-map.html` generated from finished code, checked, and shown, including a project-grounded practice to reuse

Activity and evidence: [what actually happened; real document/test/code references; unfinished work if interrupted]
Route and stops: [actual paths and symbols; guided stops completed, or reference-only route]
Edit outcome: [tried/kept/reverted/declined/not applicable; verification if changed]
Reflection: [offered/answered/declined/already covered — personal answer belongs only in the ignored profile]
Activity mode: [live app and editor, explicit static fallback, focused alternative, prior practice, or recap]

## Revisions

