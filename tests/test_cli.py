"""
End-to-end integration tests for skillpulse CLI.
"""

from pathlib import Path
import pytest
from skillpulse.cli import main


def test_cli_lint_skills_valid(capsys):
    exit_code = main(["lint-skills", "examples/valid_skill"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "sample-analyzer" in captured.out
    assert "All rules passed" in captured.out


def test_cli_lint_skills_invalid(capsys):
    exit_code = main(["lint-skills", "examples/invalid_skill"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "SKILL001" in captured.out


def test_cli_test_mcp_valid(capsys):
    exit_code = main(["test-mcp", "examples/sample_mcp_tools.json"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "get_weather" in captured.out
    assert "search_code" in captured.out
    assert "post_comment" in captured.out


def test_cli_scan_full(capsys):
    exit_code = main(["scan", ".", "--mcp-config", "examples/sample_mcp_tools.json"])
    captured = capsys.readouterr()
    assert "Ecosystem Health Score" in captured.out
    assert "Agent Skills Validation" in captured.out
    assert "Model Context Protocol" in captured.out
