import json
from pathlib import Path

from app.db.seed import seed_exchange_rates_if_empty
from tests.conftest import TestingSessionLocal


def auth_headers(ip: str) -> dict[str, str]:
    return {
        "x-api-token": "dev-token-change-me",
        "X-Forwarded-For": ip,
    }


def _seed_once() -> None:
    db = TestingSessionLocal()
    try:
        seed_exchange_rates_if_empty(db, "tests/currencies.json")
    finally:
        db.close()


def test_latest_usd_rate(client):
    _seed_once()

    latest = client.get(
        "/api/v1/rates/latest",
        params={"target_currency": "AAVE", "base_currency": "USD"},
        headers=auth_headers("203.0.113.11"),
    )
    assert latest.status_code == 200
    latest_data = latest.json()

    fixture = json.loads(Path("tests/currencies.json").read_text(encoding="utf-8"))
    aave_dates = [row["date"] for row in fixture if row["currency"] == "AAVE"]
    assert latest_data["date"] == max(aave_dates)
    assert latest_data["base_currency"] == "USD"
    assert latest_data["target_currency"] == "AAVE"
    assert "rate" in latest_data
    assert isinstance(latest_data["forward_filled"], bool)


def test_rate_limit_is_enforced(client):
    _seed_once()

    for _ in range(10):
        response = client.get(
            "/api/v1/currencies",
            headers=auth_headers("203.0.113.9"),
        )
        if response.status_code == 429:
            break
    assert response.status_code == 429


def test_list_currencies(client):
    _seed_once()

    response = client.get("/api/v1/currencies", headers=auth_headers("203.0.113.12"))
    assert response.status_code == 200

    data = response.json()
    assert data["count"] > 0
    assert len(data["items"]) == data["count"]
    assert any(item["currency"] == "AAVE" for item in data["items"])
    assert "metadata" in data
    assert data["metadata"]["total_records"] > 0
    assert data["metadata"]["number_of_currencies"] == data["count"]
    assert data["metadata"]["min_date"] <= data["metadata"]["max_date"]
    assert data["metadata"]["missing_records"] >= 0

    codes = [item["currency"] for item in data["items"]]
    assert codes == sorted(set(codes))


def test_latest_converted_rate_with_base_currency(client):
    _seed_once()

    response = client.get(
        "/api/v1/rates/latest",
        params={"target_currency": "AAVE", "base_currency": "ADA"},
        headers=auth_headers("203.0.113.13"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["base_currency"] == "ADA"
    assert data["target_currency"] == "AAVE"
    assert isinstance(data["rate"], float)


def test_historical_requires_date_range(client):
    _seed_once()

    missing = client.get(
        "/api/v1/rates/historical",
        params={"target_currency": "AAVE", "base_currency": "USD"},
        headers=auth_headers("203.0.113.14"),
    )
    assert missing.status_code == 422


def test_historical_converted_rates(client):
    _seed_once()

    response = client.get(
        "/api/v1/rates/historical",
        params={
            "target_currency": "AAVE",
            "base_currency": "USD",
            "date_from": "2024-03-01",
            "date_to": "2026-04-30",
        },
        headers=auth_headers("203.0.113.15"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    assert len(data["items"]) == data["count"]
    assert all(item["base_currency"] == "USD" for item in data["items"])
    assert all(item["target_currency"] == "AAVE" for item in data["items"])
    assert all("forward_filled" in item for item in data["items"])

    fixture = json.loads(Path("tests/currencies.json").read_text(encoding="utf-8"))
    earliest_aave = min(row["date"] for row in fixture if row["currency"] == "AAVE")
    first_date = data["items"][0]["date"]
    assert first_date == earliest_aave

    dates = [item["date"] for item in data["items"]]
    assert dates == sorted(dates)

    from datetime import date as dt_date

    parsed = [dt_date.fromisoformat(d) for d in dates]
    for prev, current in zip(parsed, parsed[1:]):
        assert (current - prev).days == 1

    assert any(item["forward_filled"] for item in data["items"])


def test_historical_converted_rates_post(client):
    _seed_once()
    response = client.post(
        "/api/v1/rates/historical",
        json={
            "target_currency": "AAVE",
            "base_currency": "USD",
            "date_from": "2024-03-01",
            "date_to": "2026-04-30",
        },
        headers=auth_headers("203.0.113.16"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    assert all(item["target_currency"] == "AAVE" for item in data["items"])


def test_historical_converted_rates_put(client):
    _seed_once()
    response = client.put(
        "/api/v1/rates/historical",
        json={
            "target_currency": "AAVE",
            "base_currency": "USD",
            "date_from": "2024-03-01",
            "date_to": "2026-04-30",
        },
        headers=auth_headers("203.0.113.17"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    assert all(item["base_currency"] == "USD" for item in data["items"])


def test_auth_required(client):
    _seed_once()
    response = client.get(
        "/api/v1/currencies", headers={"X-Forwarded-For": "203.0.113.18"}
    )
    assert response.status_code == 401


def test_put_update_delete_source_record_flow(client):
    _seed_once()

    # 1) PUT old date record (year 2000)
    create_resp = client.put(
        "/api/v1/rates/source-record",
        json={
            "target_currency": "ZZZ",
            "date": "2000-01-01",
            "rate": 2.5,
            "currency_name": "Legacy Test Currency",
        },
        headers=auth_headers("203.0.113.19"),
    )
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["currency"] == "ZZZ"
    assert created["date"] == "2000-01-01"
    assert created["rate"] == 2.5

    # Verify write is persisted via historical query.
    verify_resp = client.get(
        "/api/v1/rates/historical",
        params={
            "target_currency": "ZZZ",
            "base_currency": "USD",
            "date_from": "2000-01-01",
            "date_to": "2000-01-01",
        },
        headers=auth_headers("203.0.113.20"),
    )
    assert verify_resp.status_code == 200
    verify = verify_resp.json()
    assert verify["count"] == 1
    assert verify["items"][0]["target_currency"] == "ZZZ"
    assert verify["items"][0]["date"] == "2000-01-01"
    assert verify["items"][0]["rate"] == 2.5

    # 2) PUT same record with updated rate.
    update_resp = client.put(
        "/api/v1/rates/source-record",
        json={
            "target_currency": "ZZZ",
            "date": "2000-01-01",
            "rate": 3.75,
            "currency_name": "Legacy Test Currency",
        },
        headers=auth_headers("203.0.113.21"),
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["rate"] == 3.75

    verify_update_resp = client.get(
        "/api/v1/rates/historical",
        params={
            "target_currency": "ZZZ",
            "base_currency": "USD",
            "date_from": "2000-01-01",
            "date_to": "2000-01-01",
        },
        headers=auth_headers("203.0.113.22"),
    )
    assert verify_update_resp.status_code == 200
    assert verify_update_resp.json()["items"][0]["rate"] == 3.75

    # 3) Delete and verify removed.
    delete_resp = client.delete(
        "/api/v1/rates/source-record",
        headers=auth_headers("203.0.113.23"),
        params={"target_currency": "ZZZ", "date": "2000-01-01"},
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["deleted"] is True

    verify_delete_resp = client.get(
        "/api/v1/rates/historical",
        params={
            "target_currency": "ZZZ",
            "base_currency": "USD",
            "date_from": "2000-01-01",
            "date_to": "2000-01-01",
        },
        headers=auth_headers("203.0.113.24"),
    )
    assert verify_delete_resp.status_code == 200
    assert verify_delete_resp.json()["count"] == 0
