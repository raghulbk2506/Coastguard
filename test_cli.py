"""Tests for CLI invocation, stdin, and shell exit codes."""

import json
from click.testing import CliRunner
from costguard.cli.main import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "CostGuard" in result.output


def test_cli_plan_a_pass():
    runner = CliRunner()
    result = runner.invoke(main, ["--plan", "test-plans/plan_a_small_add.json", "--max-increase", "50"])
    assert result.exit_code == 0
    assert "PASSED" in result.output


def test_cli_plan_b_fail_threshold():
    runner = CliRunner()
    result = runner.invoke(main, ["--plan", "test-plans/plan_b_upgrade_delete.json", "--max-increase", "20"])
    assert result.exit_code == 1
    assert "FAILED" in result.output
    assert "CIRCUIT BREAKER" in result.output


def test_cli_stdin_pipe():
    runner = CliRunner()
    with open("test-plans/plan_a_small_add.json", "r") as f:
        content = f.read()
    result = runner.invoke(main, ["--max-increase", "50"], input=content)
    assert result.exit_code == 0
    assert "PASSED" in result.output


def test_cli_invalid_json():
    runner = CliRunner()
    result = runner.invoke(main, [], input="{not valid json}")
    assert result.exit_code == 2
    assert "Invalid Terraform JSON" in result.output


def test_cli_missing_file():
    runner = CliRunner()
    result = runner.invoke(main, ["--plan", "non_existent_file.json"])
    assert result.exit_code == 2
    assert "not found" in result.output


def test_cli_json_flag():
    runner = CliRunner()
    result = runner.invoke(main, ["--plan", "test-plans/plan_a_small_add.json", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "items" in data
    assert "verdict" in data
