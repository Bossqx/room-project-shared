from fastapi import APIRouter, File, UploadFile, Query
from fastapi.responses import FileResponse
from fastapi import  HTTPException
from src.endpoints.send_to_device import publish_to_mqtt, MQTT_BROKER_HOST, MQTT_BROKER_PORT
from datetime import date, datetime
from typing import Literal, Optional
import os
import json
import io
import time
import paho.mqtt.client as mqtt

router = APIRouter(
    prefix="/send-mqtt",
    tags=["send-mqtt"],
    responses={404: {"description": "Not found"}},
)


@router.get("/status")
def mqtt_status():
    client = mqtt.Client(client_id=f"health-check-{int(time.time() * 1000)}")
    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=5)
        client.disconnect()
        return {
            "status":  "ok",
            "broker":  MQTT_BROKER_HOST,
            "port":    MQTT_BROKER_PORT,
            "checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MQTT broker unreachable: {e}")


@router.get("/send_refresh_booking/")
def send_refresh_booking(status: str = "booking_schedule"):
    payload = json.dumps({
        "status": status,
        "date":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    publish_to_mqtt("mq_update_schedule", payload)
    return {"status": status, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


@router.get("/send_refresh_cancel/")
def send_refresh_cancel(status: str = "cancel_schedule"):
    payload = json.dumps({
        "status": status,
        "date":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    publish_to_mqtt("mq_update_schedule", payload)
    return {"status": status, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
