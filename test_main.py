from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

AUTH_HEADERS = {"X-API-Key": "techstar-fde-key-001"}


# ============================================================
# AUTHENTICATION TESTS
# ============================================================


def test_missing_api_key():
    response = client.get("/shipments")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key"


def test_invalid_api_key():
    response = client.get(
        "/shipments",
        headers={"X-API-Key": "wrong-key"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid API key"


# ============================================================
# SHIPMENT TESTS
# ============================================================


def test_get_shipments():
    response = client.get(
        "/shipments",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert len(response.json()) >= 3


def test_get_shipment_success():
    response = client.get(
        "/shipments/SH001",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["shipment_id"] == "SH001"


def test_get_shipment_not_found():
    response = client.get(
        "/shipments/UNKNOWN",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 404


# ============================================================
# CREATE SHIPMENT TESTS
# ============================================================


def test_create_shipment():
    shipment = {
        "shipment_id": "SH100",
        "carrier": "dhl",
        "origin": "Berlin",
        "destination": "Munich",
        "cost_usd": 150.0,
    }

    response = client.post(
        "/shipments",
        json=shipment,
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    assert response.json()["carrier"] == "DHL"


def test_invalid_carrier():
    shipment = {
        "shipment_id": "SH101",
        "carrier": "UPS",
        "origin": "Berlin",
        "destination": "Munich",
        "cost_usd": 150.0,
    }

    response = client.post(
        "/shipments",
        json=shipment,
        headers=AUTH_HEADERS,
    )

    # Carrier is accepted by the current API,
    # so this confirms the request is valid.
    assert response.status_code == 422


def test_duplicate_shipment():
    shipment = {
        "shipment_id": "SH001",
        "carrier": "DHL",
        "origin": "Berlin",
        "destination": "Munich",
        "cost_usd": 100.0,
    }

    response = client.post(
        "/shipments",
        json=shipment,
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 409


# ============================================================
# CARRIER TEST
# ============================================================


def test_get_carriers():
    response = client.get(
        "/carriers",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert len(response.json()) == 3


# ============================================================
# SUPPLY CHAIN AGGREGATION TEST
# ============================================================


def test_supply_chain_all_vendors_success():
    response = client.get(
        "/supply-chain-status/SH001",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert len(response.json()) == 3

def test_supply_chain_one_vendor_failure():
    async def failing_vendor(shipment_id: str):
        raise ConnectionError("Vendor unavailable")

    with patch(
        "main.fetch_vendor_b",
        new=AsyncMock(side_effect=ConnectionError("Vendor unavailable")),
    ):
        response = client.get(
            "/supply-chain-status/SH001",
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_supply_chain_all_vendors_failure():
    with patch(
        "main.fetch_vendor_a",
        new=AsyncMock(side_effect=ConnectionError("Vendor unavailable")),
    ), patch(
        "main.fetch_vendor_b",
        new=AsyncMock(side_effect=ConnectionError("Vendor unavailable")),
    ), patch(
        "main.fetch_vendor_c",
        new=AsyncMock(side_effect=ConnectionError("Vendor unavailable")),
    ):
        response = client.get(
            "/supply-chain-status/SH001",
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 503
