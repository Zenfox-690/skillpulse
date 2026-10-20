"""
Self-contained, interactive visual HTML diagnostic report generator for skillpulse.
Generates an offline-ready single-file HTML dashboard with embedded CSS and JavaScript.
"""

import html
import json
from pathlib import Path
from typing import Union
from skillpulse.models import ScanResult, SkillReport, MCPReport, DiagnosticIssue


class HTMLReporter:
    """Compiles a ScanResult into a polished standalone HTML dashboard."""

    @classmethod
    def generate(cls, scan_result: ScanResult, output_path: Union[str, Path] = "skillpulse-report.html") -> Path:
        output_file = Path(output_path).resolve()
        html_content = cls.build_html(scan_result)
        output_file.write_text(html_content, encoding="utf-8")
        return output_file

    @classmethod
    def build_html(cls, scan: ScanResult) -> str:
        score = scan.health_score
        grade = scan.grade
        total_skills = len(scan.skills)
        total_tools = len(scan.mcp_report.tools) if scan.mcp_report else 0
        total_errors = scan.total_errors
        total_warnings = scan.total_warnings

        score_color = "#10b981" if score >= 90 else ("#06b6d4" if score >= 80 else ("#f59e0b" if score >= 70 else "#ef4444"))

        # Render Skills Cards
        skills_html = []
        for s in scan.skills:
            status_badge = '<span class="badge badge-pass">VALID</span>' if s.is_valid else '<span class="badge badge-error">INVALID</span>'
            token_pct = min(100, int((s.token_count / 2500) * 100))
            token_bar_color = "#10b981" if s.token_count <= 2500 else "#f59e0b"

            tools_badges = "".join([f'<span class="tool-tag">{html.escape(t)}</span>' for t in s.referenced_tools])
            if not tools_badges:
                tools_badges = '<span style="color: #6b7280; font-size: 0.85rem;">None</span>'

            issues_html = []
            for issue in s.issues:
                sev_cls = "sev-error" if issue.severity == "ERROR" else ("sev-warn" if issue.severity == "WARNING" else "sev-info")
                line_str = f" [Line {issue.line_number}]" if issue.line_number else ""
                fix_str = f'<div class="fix-box"><strong>Remediation:</strong> {html.escape(issue.suggestion)}</div>' if issue.suggestion else ""
                issues_html.append(f"""
                <div class="issue-item {sev_cls}" data-severity="{issue.severity}">
                  <div class="issue-header">
                    <span class="badge badge-{issue.severity.lower()}">{issue.severity}</span>
                    <span class="rule-id">{html.escape(issue.rule_id)}{line_str}</span>
                    <span class="issue-msg">{html.escape(issue.message)}</span>
                  </div>
                  {fix_str}
                </div>
                """)

            if not issues_html:
                issues_content = '<div class="clean-pass">&#10003; All linter rules passed cleanly.</div>'
            else:
                issues_content = "".join(issues_html)

            skills_html.append(f"""
            <div class="card skill-card" data-name="{html.escape(s.name.lower())}">
              <div class="card-header">
                <div>
                  <h3 class="card-title">{html.escape(s.name or "Unnamed Skill")}</h3>
                  <div class="file-path">{html.escape(s.file_path)}</div>
                </div>
                <div>{status_badge}</div>
              </div>
              
              <div class="meta-row">
                <div class="meta-item">
                  <span class="meta-label">Token Footprint</span>
                  <div class="token-wrap">
                    <div class="token-bar-bg"><div class="token-bar-fill" style="width: {token_pct}%; background: {token_bar_color};"></div></div>
                    <span class="meta-val">~{s.token_count} tokens</span>
                  </div>
                </div>
                <div class="meta-item">
                  <span class="meta-label">Referenced Tools</span>
                  <div class="tools-list">{tools_badges}</div>
                </div>
              </div>

              <div class="issues-container">
                {issues_content}
              </div>
            </div>
            """)

        all_skills_str = "\n".join(skills_html) if skills_html else '<div class="empty-state">No SKILL.md files scanned.</div>'

        # Render MCP Report
        mcp_html = ""
        if scan.mcp_report:
            mcp = scan.mcp_report
            tools_cards = []
            for t in mcp.tools:
                props = t.input_schema.get("properties", {})
                reqs = t.input_schema.get("required", [])

                props_rows = []
                for p_name, p_data in props.items():
                    p_type = p_data.get("type", "any") if isinstance(p_data, dict) else "any"
                    p_desc = p_data.get("description", "") if isinstance(p_data, dict) else ""
                    is_req = '<span style="color:#ef4444; font-weight:bold;">Yes</span>' if p_name in reqs else '<span style="color:#9ca3af;">No</span>'
                    props_rows.append(f"""
                    <tr>
                      <td><code>{html.escape(p_name)}</code></td>
                      <td><code>{html.escape(str(p_type))}</code></td>
                      <td>{is_req}</td>
                      <td>{html.escape(str(p_desc))}</td>
                    </tr>
                    """)

                props_table = f"""
                <table class="params-table">
                  <thead><tr><th>Parameter</th><th>Type</th><th>Required</th><th>Description</th></tr></thead>
                  <tbody>{"".join(props_rows)}</tbody>
                </table>
                """ if props_rows else '<div style="color:#6b7280; font-size: 0.85rem; padding: 0.5rem 0;">No parameters required.</div>'

                tools_cards.append(f"""
                <div class="tool-card">
                  <div class="tool-card-head">
                    <span class="tool-func-name">&#9881; {html.escape(t.name)}</span>
                    <span class="badge badge-info">MCP 2025-11-25</span>
                  </div>
                  <p class="tool-desc">{html.escape(t.description or "No description provided.")}</p>
                  <div class="schema-box">
                    <span class="schema-title">Input Schema Parameters:</span>
                    {props_table}
                  </div>
                </div>
                """)

            mcp_issues_html = []
            for issue in mcp.issues:
                sev_cls = "sev-error" if issue.severity == "ERROR" else ("sev-warn" if issue.severity == "WARNING" else "sev-info")
                fix_str = f'<div class="fix-box"><strong>Remediation:</strong> {html.escape(issue.suggestion)}</div>' if issue.suggestion else ""
                mcp_issues_html.append(f"""
                <div class="issue-item {sev_cls}" data-severity="{issue.severity}">
                  <div class="issue-header">
                    <span class="badge badge-{issue.severity.lower()}">{issue.severity}</span>
                    <span class="rule-id">{html.escape(issue.rule_id)}</span>
                    <span class="issue-msg">{html.escape(issue.message)}</span>
                  </div>
                  {fix_str}
                </div>
                """)

            mcp_issues_content = "".join(mcp_issues_html) if mcp_issues_html else '<div class="clean-pass">&#10003; All MCP contract rules passed cleanly.</div>'

            ghost_alert = ""
            if mcp.ghost_tools:
                ghost_items = "".join([f"<li><code>{html.escape(g)}</code> &mdash; referenced in skill instructions but undefined in MCP tools!</li>" for g in mcp.ghost_tools])
                ghost_alert = f"""
                <div class="alert alert-danger">
                  <strong style="font-size: 1.05rem;">&#9888; Ghost Tools Detected ({len(mcp.ghost_tools)}):</strong>
                  <p style="margin: 0.35rem 0 0.5rem 0;">The following tools are called in your Agent Skills prompts but never defined in the MCP tools manifest:</p>
                  <ul style="margin-left: 1.5rem; line-height: 1.6;">{ghost_items}</ul>
                </div>
                """

            mcp_html = f"""
            <div class="card">
              <div class="card-header">
                <div>
                  <h3 class="card-title">MCP Tool Contracts &amp; Schemas</h3>
                  <div class="file-path">{html.escape(mcp.source_file)} &middot; Protocol Standard: {html.escape(mcp.protocol_version)}</div>
                </div>
                <div><span class="badge badge-info">{len(mcp.tools)} Declared Tools</span></div>
              </div>

              {ghost_alert}

              <div class="issues-container" style="margin-bottom: 1.5rem;">
                {mcp_issues_content}
              </div>

              <h4 style="color: #fff; margin-bottom: 1rem; font-size: 1.1rem;">Verified MCP Tool Catalog</h4>
              <div class="tools-grid">
                {"".join(tools_cards)}
              </div>
            </div>
            """
        else:
            mcp_html = """
            <div class="card">
              <h3 class="card-title">Model Context Protocol (MCP)</h3>
              <p style="color: #9ca3af; margin-top: 0.5rem;">No MCP tools definition file (e.g. <code>mcp_tools.json</code>) was discovered during this scan.</p>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>skillpulse &mdash; Diagnostics &amp; Health Report</title>
  <style>
    :root {{
      --bg: #090d16;
      --card-bg: rgba(18, 24, 38, 0.8);
      --card-border: rgba(255, 255, 255, 0.08);
      --primary: #06b6d4;
      --accent: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --font-mono: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
      --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: radial-gradient(circle at 50% 0%, #152238 0%, var(--bg) 70%);
      color: var(--text);
      font-family: var(--font-sans);
      line-height: 1.6;
      padding: 2.5rem 1.5rem;
      min-height: 100vh;
    }}

    .container {{ max-width: 1100px; margin: 0 auto; }}

    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
      flex-wrap: wrap;
      gap: 1rem;
    }}

    .logo-block h1 {{
      font-size: 2.5rem;
      font-weight: 800;
      letter-spacing: -0.03em;
      background: linear-gradient(135deg, #ffffff 30%, var(--primary) 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      line-height: 1.1;
    }}

    .logo-block p {{ color: var(--text-muted); font-size: 0.95rem; margin-top: 0.25rem; }}

    /* KPI Summary Row */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.25rem;
      margin-bottom: 2rem;
    }}

    .kpi-card {{
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 1.25rem;
      text-align: center;
    }}

    .kpi-val {{
      font-size: 2.25rem;
      font-weight: 800;
      line-height: 1.1;
      margin-bottom: 0.25rem;
    }}

    .kpi-label {{
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    /* Filter Bar */
    .filter-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #111827;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 0.75rem 1.25rem;
      margin-bottom: 2rem;
      flex-wrap: wrap;
      gap: 1rem;
    }}

    .filter-group {{ display: flex; gap: 0.5rem; }}

    .btn {{
      background: #1f2937;
      color: var(--text);
      border: 1px solid rgba(255, 255, 255, 0.1);
      padding: 0.4rem 0.9rem;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }}

    .btn.active {{
      background: rgba(6, 182, 212, 0.2);
      color: var(--primary);
      border-color: var(--primary);
    }}

    .search-input {{
      background: #090d16;
      border: 1px solid var(--card-border);
      color: #fff;
      padding: 0.45rem 1rem;
      border-radius: 6px;
      font-size: 0.85rem;
      width: 240px;
    }}

    /* Cards */
    .card {{
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 1.75rem;
      margin-bottom: 1.75rem;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }}

    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1rem;
    }}

    .card-title {{ font-size: 1.35rem; font-weight: 700; color: #fff; }}
    .file-path {{ font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-muted); margin-top: 0.2rem; }}

    .meta-row {{
      display: flex;
      gap: 2rem;
      padding: 0.85rem 0;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      margin-bottom: 1.25rem;
      flex-wrap: wrap;
    }}

    .meta-item {{ display: flex; flex-direction: column; gap: 0.25rem; }}
    .meta-label {{ font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; }}
    .meta-val {{ font-size: 0.85rem; color: #fff; font-weight: 600; }}

    .token-wrap {{ display: flex; align-items: center; gap: 0.75rem; }}
    .token-bar-bg {{ width: 120px; height: 8px; background: #1f2937; border-radius: 9999px; overflow: hidden; }}
    .token-bar-fill {{ height: 100%; border-radius: 9999px; }}

    .tool-tag {{
      display: inline-block;
      font-family: var(--font-mono);
      font-size: 0.75rem;
      background: rgba(6, 182, 212, 0.15);
      color: var(--primary);
      border: 1px solid rgba(6, 182, 212, 0.3);
      padding: 0.15rem 0.5rem;
      border-radius: 4px;
      margin-right: 0.35rem;
    }}

    /* Badges */
    .badge {{
      display: inline-block;
      padding: 0.25rem 0.65rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .badge-pass {{ background: rgba(16, 185, 129, 0.2); color: var(--accent); border: 1px solid rgba(16, 185, 129, 0.4); }}
    .badge-error {{ background: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.4); }}
    .badge-warning {{ background: rgba(245, 158, 11, 0.2); color: var(--warning); border: 1px solid rgba(245, 158, 11, 0.4); }}
    .badge-info {{ background: rgba(6, 182, 212, 0.2); color: var(--primary); border: 1px solid rgba(6, 182, 212, 0.4); }}

    /* Issues */
    .issue-item {{
      border-radius: 8px;
      padding: 0.85rem 1rem;
      margin-bottom: 0.75rem;
      border: 1px solid transparent;
    }}

    .issue-item.sev-error {{ background: rgba(239, 68, 68, 0.08); border-color: rgba(239, 68, 68, 0.25); }}
    .issue-item.sev-warn {{ background: rgba(245, 158, 11, 0.08); border-color: rgba(245, 158, 11, 0.25); }}
    .issue-item.sev-info {{ background: rgba(6, 182, 212, 0.08); border-color: rgba(6, 182, 212, 0.25); }}

    .issue-header {{ display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }}
    .rule-id {{ font-family: var(--font-mono); font-weight: 700; color: #fff; font-size: 0.85rem; }}
    .issue-msg {{ font-size: 0.9rem; color: #e5e7eb; }}

    .fix-box {{
      margin-top: 0.5rem;
      padding: 0.5rem 0.75rem;
      background: #090d16;
      border-radius: 6px;
      font-size: 0.85rem;
      color: #93c5fd;
      border-left: 3px solid var(--primary);
    }}

    .clean-pass {{
      padding: 0.75rem 1rem;
      background: rgba(16, 185, 129, 0.08);
      border: 1px solid rgba(16, 185, 129, 0.2);
      border-radius: 8px;
      color: var(--accent);
      font-size: 0.9rem;
      font-weight: 600;
    }}

    .alert {{
      padding: 1rem 1.25rem;
      border-radius: 10px;
      margin-bottom: 1.5rem;
    }}
    .alert-danger {{ background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.35); color: #fca5a5; }}

    /* Tools Grid */
    .tools-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 1.25rem;
    }}

    .tool-card {{
      background: #111827;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1.25rem;
    }}

    .tool-card-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.5rem;
    }}

    .tool-func-name {{ font-family: var(--font-mono); font-weight: 700; color: #fff; font-size: 0.95rem; }}
    .tool-desc {{ font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem; line-height: 1.4; }}

    .schema-title {{ font-size: 0.75rem; font-weight: 700; color: var(--primary); text-transform: uppercase; margin-bottom: 0.4rem; display: block; }}

    table.params-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8rem;
    }}
    table.params-table th {{ text-align: left; padding: 0.3rem 0.5rem; background: #0b0f19; color: var(--text-muted); border-bottom: 1px solid var(--card-border); }}
    table.params-table td {{ padding: 0.35rem 0.5rem; border-bottom: 1px solid rgba(255, 255, 255, 0.04); }}

    footer {{
      text-align: center;
      margin-top: 3.5rem;
      color: var(--text-muted);
      font-size: 0.85rem;
      border-top: 1px solid var(--card-border);
      padding-top: 1.5rem;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="logo-block">
        <h1>skillpulse</h1>
        <p>AI Agent Skills &amp; Model Context Protocol (MCP 2025-11-25) Diagnostics Dashboard</p>
      </div>
      <div style="text-align: right;">
        <span class="badge badge-info">{html.escape(scan.timestamp or "Live Run")}</span>
        <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.35rem;">Workspace: {html.escape(scan.workspace_path)}</div>
      </div>
    </header>

    <!-- KPI Row -->
    <div class="kpi-grid">
      <div class="kpi-card" style="border-top: 3px solid {score_color};">
        <div class="kpi-val" style="color: {score_color};">{score}%</div>
        <div class="kpi-label">Health Score &middot; Grade {grade}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val" style="color: #38bdf8;">{total_skills}</div>
        <div class="kpi-label">Skills Scanned</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val" style="color: #a78bfa;">{total_tools}</div>
        <div class="kpi-label">MCP Tools Verified</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val" style="color: {('#ef4444' if total_errors else '#10b981')};">{total_errors}</div>
        <div class="kpi-label">Critical Errors</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val" style="color: {('#f59e0b' if total_warnings else '#10b981')};">{total_warnings}</div>
        <div class="kpi-label">Warnings &amp; Suggestions</div>
      </div>
    </div>

    <!-- Filter Bar -->
    <div class="filter-bar">
      <div class="filter-group">
        <button class="btn active" onclick="filterSeverity('ALL')">All Issues</button>
        <button class="btn" onclick="filterSeverity('ERROR')">Errors Only</button>
        <button class="btn" onclick="filterSeverity('WARNING')">Warnings Only</button>
      </div>
      <input type="text" class="search-input" id="search-box" placeholder="Filter by skill or tool name..." oninput="filterSearch()">
    </div>

    <!-- Skills Section -->
    <h2 style="font-size: 1.4rem; color: #fff; margin-bottom: 1.25rem;">Scanned Agent Skills</h2>
    <div id="skills-list">
      {all_skills_str}
    </div>

    <!-- MCP Section -->
    <h2 style="font-size: 1.4rem; color: #fff; margin-top: 2.5rem; margin-bottom: 1.25rem;">MCP Protocol &amp; Contract Verification</h2>
    {mcp_html}

    <footer>
      <p>Generated by skillpulse &middot; Open Source Dual-Hackathon Project (Build With AI &amp; Amazon Developer Hackathon)</p>
    </footer>
  </div>

  <script>
    let currentSeverity = 'ALL';

    function filterSeverity(sev) {{
      currentSeverity = sev;
      document.querySelectorAll('.filter-group .btn').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');
      applyFilters();
    }}

    function filterSearch() {{
      applyFilters();
    }}

    function applyFilters() {{
      const query = document.getElementById('search-box').value.toLowerCase().trim();

      // Filter Skill Cards
      document.querySelectorAll('.skill-card').forEach(card => {{
        const name = card.getAttribute('data-name') || '';
        const matchesSearch = !query || name.includes(query);

        // Check severity inside card
        const issues = card.querySelectorAll('.issue-item');
        let hasMatchingIssue = (currentSeverity === 'ALL');

        if (currentSeverity !== 'ALL') {{
          hasMatchingIssue = false;
          issues.forEach(issue => {{
            if (issue.getAttribute('data-severity') === currentSeverity) {{
              hasMatchingIssue = true;
            }}
          }});
        }}

        if (matchesSearch && hasMatchingIssue) {{
          card.style.display = 'block';
          // toggle individual issues inside card
          issues.forEach(issue => {{
            if (currentSeverity === 'ALL' || issue.getAttribute('data-severity') === currentSeverity) {{
              issue.style.display = 'block';
            }} else {{
              issue.style.display = 'none';
            }}
          }});
        }} else {{
          card.style.display = 'none';
        }}
      }});
    }}
  </script>
</body>
</html>
"""
