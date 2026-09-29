"""Tests for Budget Circuit Breaker."""

from costguard.core.guardrail import BudgetGuardrail


def test_budget_pass():
    guardrail = BudgetGuardrail(max_increase=50.0)
    verdict = guardrail.evaluate(net_delta=34.90)
    assert verdict.passed is True
    assert verdict.exit_code == 0
    assert "PASSED" in verdict.status_text
    assert verdict.overage == 0.0


def test_budget_exact_threshold_pass():
    guardrail = BudgetGuardrail(max_increase=50.0)
    verdict = guardrail.evaluate(net_delta=50.0)
    assert verdict.passed is True
    assert verdict.exit_code == 0


def test_budget_failure():
    guardrail = BudgetGuardrail(max_increase=50.0)
    verdict = guardrail.evaluate(net_delta=74.90)
    assert verdict.passed is False
    assert verdict.exit_code == 1
    assert "FAILED" in verdict.status_text
    assert verdict.overage == 24.90


def test_negative_delta_pass():
    guardrail = BudgetGuardrail(max_increase=50.0)
    verdict = guardrail.evaluate(net_delta=-15.00)
    assert verdict.passed is True
    assert verdict.exit_code == 0
