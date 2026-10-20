# skillpulse

[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-cyan.svg)](https://www.python.org/)
[![MCP Spec: 2025-11-25](https://img.shields.io/badge/MCP-2025--11--25-blue.svg)](https://spec.modelcontextprotocol.io)
[![Tests: Pytest](https://img.shields.io/badge/tests-26%20passed-brightgreen.svg)](tests/)

> Open-source developer linter, test harness, and diagnostics suite for **AI Agent Skills** (`SKILL.md`) and **Model Context Protocol** (`MCP 2025-11-25`) schemas and contracts.

---

## Overview

As autonomous coding agents (Claude Code, Antigravity, Cursor, OpenAI Codex) proliferate, developers lack automated tooling to validate agent skills and MCP tools before deployment. Malformed YAML frontmatter, oversized context prompt bloat, and broken tool parameter schemas silently degrade agent performance.

`skillpulse` solves this by providing a unified, sub-millisecond developer bridge that:
1. **Lints Agent Skills (`SKILL.md`):** Validates YAML frontmatter, checks required attributes, detects trigger keywords, and estimates token consumption (~1.3 tokens/word).
2. **Validates MCP 2025-11-25 Schemas:** Validates tool definitions against the latest Model Context Protocol schema standards.
3. **Catches Ghost & Orphaned Tools:** Cross-checks prompt tool references against MCP declarations to catch tools called by skills that don't exist in MCP, or declared MCP tools that are never documented.
4. **Computes Ecosystem Health Score:** Produces a deterministic 0–100% Health Score with letter grades (A/B/C/F) for CI/CD pipelines.
5. **Generates Visual HTML Dashboard:** Compiles a standalone, offline-ready interactive report (`skillpulse-report.html`) with embedded filtering and copyable remediation diffs.

---

## Rules Evaluated

### Agent Skill Rules (`SKILL.md`)
| Rule ID | Severity | Name | Description |
| :--- | :--- | :--- | :--- |
| `SKILL001` | **Error** | Frontmatter Delimiters | Must begin and end with valid `---` YAML frontmatter delimiters. |
| `SKILL002` | **Error** | Skill Name | Attribute `name` required (1–64 characters, lowercase alphanumeric/hyphens). |
| `SKILL003` | **Error** | Description | Attribute `description` required (action-oriented purpose). |
| `SKILL004` | **Warning** | Trigger Guidance | Emits warning if explicit activation keywords/triggers are missing. |
| `SKILL005` | **Warning** | Token Budget | Flags prompts exceeding 2,500 estimated tokens to prevent context bloat. |

### MCP 2025-11-25 Protocol Rules
| Rule ID | Severity | Name | Description |
| :--- | :--- | :--- | :--- |
| `MCP001` | **Error** | Protocol Format | Requires valid MCP 2025-11-25 tool structure (array of tool objects). |
| `MCP002` | **Error** | Schema Completeness | Tools require `name`, `description`, and `inputSchema` (`type: "object"`). |
| `MCP003` | **Error** | Ghost Tool Detection | Flags tools called in `SKILL.md` prompts that are not defined in MCP. |
| `MCP004` | **Info** | Orphaned Tool | Flags declared MCP tools that are never referenced across agent skills. |

---

## Quickstart

### Installation (Local Dev)
```powershell
# Clone repository
git clone https://github.com/your-username/skillpulse.git
cd skillpulse

# Run full scan across workspace
python -m skillpulse scan

# Or scan specific skills directory and MCP configuration
python -m skillpulse scan --skills-dir .agents/skills --mcp-config examples/sample_mcp_tools.json
```

### Subcommands
```powershell
# 1. Lint skills only
python -m skillpulse lint-skills .agents/skills

# 2. Test MCP tool contracts & schemas
python -m skillpulse test-mcp examples/sample_mcp_tools.json

# 3. Generate visual HTML report
python -m skillpulse report --output skillpulse-report.html
```

---

## Running the Automated Test Suite

`skillpulse` is tested with `pytest`:

```powershell
python -m pytest tests/ -v
```

All 26 test cases validate linter rules, YAML parsing, MCP contract cross-checking, scoring calculations, and CLI integration.

---

## Dual-Hackathon Objectives

This project was built to satisfy:
1. **Build With AI: Basics (`learn-ai-basics.devpost.com`)**: Created using the flipped-interaction Devpost Learn Skill Pack workflow (`1-start` &rarr; `2-scope` &rarr; `3-prd` &rarr; `4-spec` &rarr; `5-build` &rarr; `6-ship`).
2. **Amazon Developer Hackathon — Open Source Mini Challenge (`amazonappdev2026.devpost.com`)**: Advances open-source developer tooling for the Agent Skills and Model Context Protocol ecosystem under the MIT License.

---

## License

MIT License. Copyright (c) 2026 Demo Builder. See [LICENSE](LICENSE) for details.
