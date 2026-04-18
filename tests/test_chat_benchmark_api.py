from __future__ import annotations

from fastapi.testclient import TestClient

from thalos_prime.api.server import app

client = TestClient(app)


def test_benchmark_tasks_endpoint() -> None:
    response = client.get('/api/v1/chat/benchmark/tasks')
    assert response.status_code == 200
    payload = response.json()
    assert payload['benchmark'] == 'latent_pattern_recovery_v1'
    assert payload['count'] >= 10
    assert isinstance(payload['tasks'], list)


def test_run_benchmark_endpoint_returns_artifact() -> None:
    response = client.post('/api/v1/chat/benchmark/run?task_id=latent-11&seed=2026&perturbation=0')
    assert response.status_code == 200
    payload = response.json()
    assert payload['task_id'] == 'latent-11'
    assert payload['constraints_pass'] is True
    assert payload['stabilized'] is True
    assert 'artifact' in payload
    assert payload['artifact']['selected_answer']['search_top_result']['address'] == payload['selected_address']


def test_run_benchmark_invalid_task_returns_404() -> None:
    response = client.post('/api/v1/chat/benchmark/run?task_id=does-not-exist&seed=1&perturbation=0')
    assert response.status_code == 404


def test_compare_benchmark_endpoint_reports_outperformance() -> None:
    response = client.post('/api/v1/chat/benchmark/compare?seed=2026&perturbation=0')
    assert response.status_code == 200
    payload = response.json()

    assert payload['task_count'] >= 10
    summary = payload['summary']
    assert summary['operational_outperforms_both_means'] is True
    assert summary['operational_vs_noisy_win_rate'] >= 0.65
    assert summary['operational_vs_random_win_rate'] >= 0.75
