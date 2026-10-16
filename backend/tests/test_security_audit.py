import io
import pytest
from app.analytics.exporter import sanitize_csv_cell
from app.core.rate_limit import InMemoryRateLimiter


def test_formula_injection_defense_with_leading_spaces_and_special_chars():
    """Verify formula injection handles leading whitespace, tabs, and alternative formula triggers."""
    dangerous = [
        "  =cmd|' /C calc'!A0",
        "\t=SUM(1,2)",
        "   +10-2",
        "  -5*10",
        "  @AVERAGE(A1:A10)",
        "|calc.exe",
        "  %OS%",
    ]
    for cell in dangerous:
        sanitized = sanitize_csv_cell(cell)
        assert sanitized.startswith("'"), f"Failed to sanitize: {cell} -> {sanitized}"


def test_password_length_limits(client):
    """Verify password max length is strictly enforced to prevent Argon2 DoS."""
    oversized_password = "P" * 129
    res = client.post("/api/v1/auth/register", json={
        "email": "dos_tester@querypilot.dev",
        "password": oversized_password
    })
    assert res.status_code == 422


def test_dataset_analyses_enumeration_forbidden(client, auth_headers):
    """Verify that querying analyses for another user's dataset returns 403 Forbidden."""
    # User 2 uploads a dataset
    u2 = client.post("/api/v1/auth/register", json={
        "email": "user2_audit@querypilot.dev",
        "password": "Password123!"
    }).json()
    u2_headers = {"Authorization": f"Bearer {u2['access_token']}"}

    csv_content = "id,value\n1,100\n"
    ds_res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("u2_data.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
        headers=u2_headers
    )
    assert ds_res.status_code == 201
    u2_dataset_id = ds_res.json()["id"]

    # User 1 attempts to query analyses for User 2's dataset
    forbidden_list = client.get(f"/api/v1/analyses?dataset_id={u2_dataset_id}", headers=auth_headers)
    assert forbidden_list.status_code == 403


def test_ambiguous_question_handling(client, auth_headers):
    """Verify that ambiguous or unrelated questions request clarification rather than inventing a result."""
    csv_content = "product,revenue\nLaptop,1000\n"
    ds_res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("clarify_test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
        headers=auth_headers
    )
    ds_id = ds_res.json()["id"]

    # Ask completely unrelated question
    res = client.post(
        "/api/v1/analyses",
        json={"dataset_id": ds_id, "question": "What is the capital city of France?"},
        headers=auth_headers
    )
    assert res.status_code == 400
    assert "ambiguous" in res.json()["detail"].lower() or "clarify" in res.json()["detail"].lower()


def test_column_explosion_limit_defense(client, auth_headers):
    """Verify CSV with excessive columns (> 500) is rejected to protect against resource exhaustion."""
    cols = [f"col_{i}" for i in range(505)]
    header_line = ",".join(cols)
    data_line = ",".join(["1"] * 505)
    bomb_csv = f"{header_line}\n{data_line}\n"

    res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("column_bomb.csv", io.BytesIO(bomb_csv.encode("utf-8")), "text/csv")},
        headers=auth_headers
    )
    assert res.status_code == 400
    assert "maximum allowed column count" in res.json()["detail"]


def test_in_memory_rate_limiter_logic():
    """Verify rate limiter blocks when threshold is exceeded."""
    from unittest.mock import MagicMock
    limiter = InMemoryRateLimiter(requests_per_minute=3, window_seconds=60)
    mock_req = MagicMock()
    mock_req.client.host = "192.168.1.100"

    # First 3 requests succeed
    limiter.check(mock_req)
    limiter.check(mock_req)
    limiter.check(mock_req)

    # 4th request must raise 429
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        limiter.check(mock_req)
    assert exc.value.status_code == 429
