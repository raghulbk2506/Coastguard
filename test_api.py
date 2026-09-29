"""Tests for FastAPI backend REST endpoints."""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_api_list_test_plans():
    response = client.get("/api/test-plans")
    assert response.status_code == 200
    plans = response.json()
    assert len(plans) == 4
    plan_ids = [p["id"] for p in plans]
    assert "plan_a" in plan_ids
    assert "plan_b" in plan_ids
    assert "plan_c" in plan_ids


def test_api_run_demo_plan_a():
    response = client.post("/api/analyze/demo/plan_a")
    assert response.status_code == 200
    data = response.json()
    assert data["net_delta"] == 27.30
    assert data["verdict"]["passed"] is True


def test_api_run_demo_plan_b():
    response = client.post("/api/analyze/demo/plan_b?max_increase=50")
    assert response.status_code == 200
    data = response.json()
    assert data["prior_total"] == 15.18
    assert data["projected_total"] == 50.08
    assert data["net_delta"] == 34.90
    assert data["verdict"]["passed"] is True


def test_api_run_demo_plan_b_over_budget():
    response = client.post("/api/analyze/demo/plan_b?max_increase=20")
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"]["passed"] is False
    assert data["verdict"]["exit_code"] == 1


def test_api_run_demo_plan_c_hostile():
    response = client.post("/api/analyze/demo/plan_c")
    assert response.status_code == 200
    data = response.json()
    assert data["net_delta"] == 0.0
    assert len(data["skipped_resources"]) == 15


def test_api_cache_endpoints():
    response = client.get("/api/cache")
    assert response.status_code == 200
    data = response.json()
    assert "stats" in data
    assert "entries" in data


def test_api_guardrails():
    get_res = client.get("/api/guardrails")
    assert get_res.status_code == 200
    assert "max_increase" in get_res.json()

    put_res = client.put(
        "/api/guardrails",
        json={"max_increase": 75.0, "currency": "USD", "warning_threshold_pct": 85.0, "deployment_blocking": True},
    )
    assert put_res.status_code == 200
    assert put_res.json()["settings"]["max_increase"] == 75.0
