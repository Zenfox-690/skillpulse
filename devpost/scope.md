---
doc: scope
status: approved
---

# skillpulse

The open-source linter, test harness, and diagnostics suite for AI Agent Skills (`SKILL.md`) and Model Context Protocol (`MCP` 2025-11-25) servers.

## The Unique Kernel
The unified developer bridge that validates *both* Agent Skills (`SKILL.md` frontmatter, prompt structure, token budget) and Model Context Protocol servers (`2025-11-25` JSON-RPC handshake, schema validation, tool signatures) in a single high-speed command, outputting terminal diagnostics and a self-contained interactive visual HTML report with an actionable Health Score (0–100%).

## Who It's For
AI agent engineers, open-source contributors, and developers building tools for Claude Code, Antigravity, Cursor, and custom agent runtimes who currently diagnose broken skills, malformed YAML frontmatter, oversized context prompt bloat, and silent MCP server crashes through tedious trial-and-error in chat sessions.

## The Core Loop
1. The developer runs `skillpulse scan` (or `skillpulse test-mcp <server-cmd>`) in their project workspace.
2. `skillpulse` discovers all `SKILL.md` files and configured MCP servers, parsing frontmatter schemas, checking required keys, calculating token load, and executing standard JSON-RPC 2.0 handshake/tool listing tests.
3. The developer immediately receives a color-coded CLI report with concrete line-numbered issues, followed by an auto-generated visual interactive report (`skillpulse-report.html`) complete with 1-click remediation guidelines and an overall ecosystem Health Score.

## Inspiration & Identity
- **Visual Identity:** Sleek obsidian dark-mode interface with vibrant emerald (`#10b981`), electric cyan (`#06b6d4`), and amber/rose warning accents.
- **Tone & Feel:** Authoritative, lightning-fast (<500ms execution), modern developer ergonomics akin to `ruff`, `vitest`, and `fastmcp`.
- **Reference URLs:**
  - Model Context Protocol Specification: https://spec.modelcontextprotocol.io
  - Agent Skills Standard: https://skills.sh
  - Devpost Hackathon: https://learn-ai-basics.devpost.com

## Why This Matters to the Learner
As autonomous coding agents and agent skills proliferate, the developer tooling layer remains primitive. Builders need automated CI-ready validation to ensure their agent skills won't silently hallucinate or consume 40k tokens in hidden prompt bloat, and their MCP tools adhere strictly to the evolving `2025-11-25` schema standard.

## What "Working" Looks Like
A developer runs `skillpulse scan` in a project with agent skills and MCP declarations. In under 400ms, the CLI prints an organized table of diagnostics (Errors, Warnings, Token Estimates, MCP Protocol Status, Overall Health Score: e.g. 94/100). Opening the generated `skillpulse-report.html` renders an interactive visual dashboard displaying breakdown charts, collapsible issue cards, and copy-paste remediation diffs.

## The POC Boundary
- **In-Scope:**
  - Static linter for `SKILL.md` (YAML frontmatter syntax, required `name` and `description`, recommended trigger keywords, markdown structure, estimated token budget).
  - MCP Server Test Harness (JSON-RPC 2.0 stdio handshake, protocol version `2025-11-25` check, `tools/list` schema validation).
  - CLI commands: `skillpulse scan`, `skillpulse lint-skills`, `skillpulse test-mcp`, `skillpulse report`.
  - Self-contained interactive HTML report generator with embedded visual styling and zero external runtime dependencies.
  - Full automated test suite with `pytest`.
  - Open-source MIT License and clean inspectable PR structure.

## Later
- GitHub Actions CI workflow runner integration (`skillpulse-action`).
- Live SSE/HTTP streaming transport support for remote MCP endpoints.
- Automated code rewrite / auto-fix CLI command (`skillpulse fix`).
- Pre-commit hook generator.

## Explicitly Cut
- **Cloud Database / SaaS Backend:** Cut to guarantee 100% offline, privacy-first local operation without API keys or telemetry.
- **User Authentication / Multi-Tenancy:** Cut because a developer CLI & local test harness operates within the local user filesystem.
- **Monetization / Proprietary Licensing:** Cut to maintain pure MIT open-source alignment for the Amazon Developer Hackathon.
