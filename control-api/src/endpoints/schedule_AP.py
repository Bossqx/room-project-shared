from fastapi import APIRouter,Query
from pydantic import BaseModel, Field
from src.models.schedule import Schedule_Controller
from src.endpoints.send_to_device import publish_to_mqtt, MQTT_BROKER_HOST
from typing import  Optional
import json


router = APIRouter(
    prefix="/schedule_AP",
    tags=["schedule_AP"],
    responses={404: {"description": "Not found"}},
)


def _duration_seconds(start_time, finish_time) -> int:
    """Seconds from startTime to finishTime ("HH:MM"); 0 if either is unusable."""
    def to_minutes(t):
        try:
            h, m = str(t).split(":")[:2]
            return int(h) * 60 + int(m)
        except (ValueError, AttributeError):
            return None

    s, f = to_minutes(start_time), to_minutes(finish_time)
    if s is None or f is None:
        return 0
    return max(0, (f - s) * 60)


class APTarget(BaseModel):
    rowId: str = Field(..., description="Unique identifier for the target device")
    source_type: Optional[str] = Field(None, description="Optional source type for the command, e.g. 'MIS Schedule' or 'booking'")
    

class APCommandRequest(BaseModel):
    rowId:  str               = Field(..., description="Unique identifier for the command")
    topic:   str               = Field(..., description="MQTT topic to publish to")
    host:    str               = Field(MQTT_BROKER_HOST, description="MQTT broker IP or hostname")
    room:    str               = Field(..., description="Room identifier, e.g. 'room1'")
    targets: list[APTarget] = Field(..., description="One or more devices to command")
    qos:     int               = Field(1, ge=0, le=2)


@router.get("/get_booking_at_current_time/")
async def get_booking_at_current_time():
    db = Schedule_Controller()
    results=db.get_booking_at_current_time()
    return results

@router.post("/send_booking_at_current_time/")
async def send_booking_at_current_time(qos: int = Query(1, ge=0, le=2)):
    """
    Fetch bookings currently in progress and publish each one's access
    token to its room's AP topic (device/<ip_address>/<room_no>).
    """
    db = Schedule_Controller()
    bookings = db.get_booking_at_current_time()

    results = []
    errors  = []

    for booking in bookings:
        topic = booking.get("topic")
        #token = booking.get("token")
        if not topic:
            errors.append({"rowId": booking.get("rowId"), "error": "Missing topic (no room_binding)"})
            continue
        message = json.dumps({"rowId": booking.get("rowId"),"source_type": booking.get("objective"),"coursecode":booking.get("coursecode")})
        try:
            publish_to_mqtt(topic, message, qos=qos)
            results.append({"rowId": booking.get("rowId"), "topic": topic,  "source_type": booking.get("source_type"),"coursecode":booking.get("coursecode"), "sent": True})
        except Exception as exc:
            errors.append({"rowId": booking.get("rowId"), "topic": topic, "error": str(exc)})

    return {
        "success": len(errors) == 0,
        "count":   len(results),
        "results": results,
        "errors":  errors,
    }
    
    

@router.post("/AP_device/send_command")
async def send_command(request: APCommandRequest):
    """
    Publish a command to one or more devices.

    Each target produces one MQTT message:
        topic:   device/<room>/<device>
        payload: {"device_no": "<n>", "status": "<status>"}
    """
    topic   = request.topic
    results = []
    errors  = []

    for target in request.targets:
        db = Schedule_Controller()
        schedule = db.get_schedule_by_id(target.rowId, target.source_type)

        payload = {"rowId": target.rowId,"source_type": target.source_type}
        if schedule:
            schedule_date = schedule.get("schedule_date")
            payload.update({
                "coursecode":    schedule.get("coursecode"),
                "roomcode":      schedule.get("roomcode"),
                "schedule_date": schedule_date.isoformat() if schedule_date else None,
                "startTime":     schedule.get("startTime"),
                "finishTime":    schedule.get("finishTime"),
                "duration":      _duration_seconds(schedule.get("startTime"), schedule.get("finishTime")),
                "yearNo":        schedule.get("yearNo"),
                "semester":      schedule.get("semester"),
                "userCode":      schedule.get("userCode"),
            })
        message = json.dumps(payload)
        try:
            publish_to_mqtt(topic, message, qos=request.qos, host=request.host)
            results.append({**payload, "sent": True})
        except Exception as exc:
            errors.append({ "rowId":target.rowId, "source_type": target.source_type, "error": str(exc)})

    return {
        "success": len(errors) == 0,
        "host":    request.host,
        "topic":   topic,
        "results": results,
        "errors":  errors,
    }    

@router.post("/AP_device/access_token")
async def device_command(request: APCommandRequest):
    """
    Publish a command to one or more devices.

    Each target produces one MQTT message:
        topic:   device/<room>/<device>
        payload: {"device_no": "<n>", "status": "<status>"}
    """
    topic   = request.topic
    results = []
    errors  = []

    for target in request.targets:
        db = Schedule_Controller()
        schedule = db.get_schedule_by_id(target.rowId, target.source_type)

        payload = {"rowId": target.rowId,"source_type": target.source_type}
        if schedule:
            schedule_date = schedule.get("schedule_date")
            payload.update({
                "coursecode":    schedule.get("coursecode"),
                "roomcode":      schedule.get("roomcode"),
                "schedule_date": schedule_date.isoformat() if schedule_date else None,
                "startTime":     schedule.get("startTime"),
                "finishTime":    schedule.get("finishTime"),
                "duration":      _duration_seconds(schedule.get("startTime"), schedule.get("finishTime")),
                "yearNo":        schedule.get("yearNo"),
                "semester":      schedule.get("semester"),
                "userCode":      schedule.get("userCode"),
            })
        message = json.dumps(payload)
        try:
            publish_to_mqtt(topic, message, qos=request.qos, host=request.host)
            results.append({**payload, "sent": True})
        except Exception as exc:
            errors.append({ "rowId":target.rowId, "source_type": target.source_type, "error": str(exc)})

    return {
        "success": len(errors) == 0,
        "host":    request.host,
        "topic":   topic,
        "results": results,
        "errors":  errors,
    }
    
    