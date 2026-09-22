import asyncio
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

app = FastAPI(
    title="Supply Chain Status API",
    description="API for tracking shipments and carriers",
    version="1.0.0",
)


# ============================================================
# API KEY AUTHENTICATION
# ============================================================

VALID_API_KEYS = {
    "techstar-fde-key-001",
    "techstar-fde-key-002",
}


def verify_api_key(x_api_key: str | None = Header(default=None)) -> str:
    if x_api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Missing API key",
        )

    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key",
        )

    return x_api_key


# ============================================================
# MOCK DATA
# ============================================================

MOCK_SHIPMENTS: dict[str, dict[str, Any]] = {
    "SH001": {
        "shipment_id": "SH001",
        "carrier": "DHL",
        "origin": "Paris",
        "destination": "Munich",
        "status": "delayed",
        "cost_usd": 125.50,
    },
    "SH002": {
        "shipment_id": "SH002",
        "carrier": "FEDEX",
        "origin": "Hamburg",
        "destination": "Frankfurt",
        "status": "in_transit",
        "cost_usd": 98.75,
    },
    "SH003": {
        "shipment_id": "SH003",
        "carrier": "BLUEDART",
        "origin": "Delhi",
        "destination": "Mumbai",
        "status": "delivered",
        "cost_usd": 75.00,
    },
}


MOCK_CARRIERS: dict[str, dict[str, Any]] = {
    "DHL": {
        "name": "DHL",
        "country": "Germany",
        "active_shipments": 120,
    },
    "FEDEX": {
        "name": "FEDEX",
        "country": "USA",
        "active_shipments": 95,
    },
    "BLUEDART": {
        "name": "BLUEDART",
        "country": "India",
        "active_shipments": 80,
    },
}


# ============================================================
# PYDANTIC MODELS
# ============================================================


class ShipmentResponse(BaseModel):
    shipment_id: str
    carrier: str
    origin: str
    destination: str
    status: str
    cost_usd: float


class ShipmentCreateRequest(BaseModel):
    shipment_id: str = Field(min_length=3, max_length=20)
    carrier: str
    origin: str
    destination: str
    cost_usd: float = Field(gt=0)

    @field_validator("carrier")
    @classmethod
    def normalize_carrier(cls, value: str) -> str:
        normalized = value.upper()

        if normalized not in {"DHL", "FEDEX", "BLUEDART"}:
            raise ValueError("Unsupported carrier")

        return normalized


class VendorStatus(BaseModel):
    vendor: str
    shipment_id: str
    status: str
    details: dict[str, Any]


class CarrierResponse(BaseModel):
    name: str
    country: str
    active_shipments: int


# ============================================================
# MOCK VENDOR FUNCTIONS
# ============================================================


async def fetch_vendor_a(shipment_id: str) -> dict[str, Any]:
    await asyncio.sleep(0.1)

    return {
        "id": shipment_id,
        "current_status": "in_transit",
        "eta_days": 2,
    }


async def fetch_vendor_b(shipment_id: str) -> dict[str, Any]:
    await asyncio.sleep(0.1)

    return {
        "shipmentRef": shipment_id,
        "trackingState": "DELAYED",
        "delayHrs": 36,
    }


async def fetch_vendor_c(shipment_id: str) -> dict[str, Any]:
    await asyncio.sleep(0.1)

    return {
        "shipment": {
            "identifier": shipment_id,
            "state": {
                "code": "DELIVERED",
                "confidence": 0.95,
            },
        }
    }


# ============================================================
# VENDOR NORMALIZERS
# ============================================================


def normalize_vendor_a(data: dict[str, Any]) -> VendorStatus:
    return VendorStatus(
        vendor="Vendor A",
        shipment_id=data["id"],
        status=data["current_status"],
        details={
            "eta_days": data["eta_days"],
        },
    )


def normalize_vendor_b(data: dict[str, Any]) -> VendorStatus:
    return VendorStatus(
        vendor="Vendor B",
        shipment_id=data["shipmentRef"],
        status=data["trackingState"],
        details={
            "delay_hours": data["delayHrs"],
        },
    )


def normalize_vendor_c(data: dict[str, Any]) -> VendorStatus:
    shipment = data["shipment"]

    return VendorStatus(
        vendor="Vendor C",
        shipment_id=shipment["identifier"],
        status=shipment["state"]["code"],
        details={
            "confidence": shipment["state"]["confidence"],
        },
    )


# ============================================================
# EXERCISE 1 - GET ALL SHIPMENTS
# ============================================================


@app.get(
    "/shipments",
    response_model=list[ShipmentResponse],
)
def get_shipments(
    status: str | None = None,
    carrier: str | None = None,
    _api_key: str = Depends(verify_api_key),
):
    shipments = list(MOCK_SHIPMENTS.values())

    if status is not None:
        shipments = [
            shipment
            for shipment in shipments
            if str(shipment["status"]).lower() == status.lower()
        ]

    if carrier is not None:
        shipments = [
            shipment
            for shipment in shipments
            if str(shipment["carrier"]).lower() == carrier.lower()
        ]

    return shipments


# ============================================================
# EXERCISE 1 - GET ONE SHIPMENT
# ============================================================


@app.get(
    "/shipments/{shipment_id}",
    response_model=ShipmentResponse,
)
def get_shipment(
    shipment_id: str,
    _api_key: str = Depends(verify_api_key),
):
    shipment = MOCK_SHIPMENTS.get(shipment_id)

    if shipment is None:
        raise HTTPException(
            status_code=404,
            detail=f"Shipment {shipment_id} not found",
        )

    return shipment


# ============================================================
# EXERCISE 1 - CREATE SHIPMENT
# ============================================================


@app.post(
    "/shipments",
    response_model=ShipmentResponse,
    status_code=201,
)
def create_shipment(
    request: ShipmentCreateRequest,
    _api_key: str = Depends(verify_api_key),
):
    if request.shipment_id in MOCK_SHIPMENTS:
        raise HTTPException(
            status_code=409,
            detail=f"Shipment {request.shipment_id} already exists",
        )

    shipment = {
        "shipment_id": request.shipment_id,
        "carrier": request.carrier,
        "origin": request.origin,
        "destination": request.destination,
        "status": "pending",
        "cost_usd": request.cost_usd,
    }

    MOCK_SHIPMENTS[request.shipment_id] = shipment

    return shipment


# ============================================================
# EXERCISE 1 - GET CARRIERS
# ============================================================


@app.get(
    "/carriers",
    response_model=list[CarrierResponse],
)
def get_carriers(
    _api_key: str = Depends(verify_api_key),
):
    return list(MOCK_CARRIERS.values())


# ============================================================
# EXERCISE 2 - SUPPLY CHAIN STATUS
# ============================================================


@app.get(
    "/supply-chain-status/{shipment_id}",
    response_model=list[VendorStatus],
)
async def get_supply_chain_status(
    shipment_id: str,
    _api_key: str = Depends(verify_api_key),
) -> list[VendorStatus]:

    vendor_calls = await asyncio.gather(
        fetch_vendor_a(shipment_id),
        fetch_vendor_b(shipment_id),
        fetch_vendor_c(shipment_id),
        return_exceptions=True,
    )

    results: list[VendorStatus] = []

    normalizers = [
        normalize_vendor_a,
        normalize_vendor_b,
        normalize_vendor_c,
    ]

    for result, normalizer in zip(vendor_calls, normalizers):
        if isinstance(result, BaseException):
            continue

        results.append(normalizer(result))

    if not results:
        raise HTTPException(
            status_code=503,
            detail="All vendor systems are unavailable",
        )

    return results


# ============================================================
# HEALTH CHECK
# ============================================================


@app.get("/")
def root():
    return {
        "message": "Supply Chain API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }