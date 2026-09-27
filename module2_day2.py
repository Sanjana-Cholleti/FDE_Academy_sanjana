from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


def status(delaydays: int) -> str:
    if delaydays == 0:
        return "on_time"
    elif delaydays <= 2:
        return "minor_delay"
    else:
        return "major_delay"


class Shipment:
    def __init__(self, shipment_id: str, carrier: str, delaydays: int):
        self.shipment_id = shipment_id
        self.carrier = carrier
        self.delaydays = delaydays

    def status(self) -> str:
        return status(self.delaydays)


app = FastAPI()
shipments_db = {}
class ShipmentIn(BaseModel):
    carrier: str
    delaydays: int


@app.get("/shipments/{shipment_id}")
def get_shipment(shipment_id: str):
    if shipment_id not in shipments_db:
        raise HTTPException(status_code=404, detail="Shipment not found")

    shipment = shipments_db[shipment_id]

    return {
        "shipment_id": shipment.shipment_id,
        "carrier": shipment.carrier,
        "delaydays": shipment.delaydays,
        "status": shipment.status()
    }


@app.post("/shipments/{shipment_id}")
def create_shipment(shipment_id: str, shipment: ShipmentIn):
    new_shipment = Shipment(
        shipment_id,
        shipment.carrier,
        shipment.delaydays
    )

    shipments_db[shipment_id] = new_shipment

    return {
        "shipment_id": new_shipment.shipment_id,
        "carrier": new_shipment.carrier,
        "delaydays": new_shipment.delaydays,
        "status": new_shipment.status()
    }
