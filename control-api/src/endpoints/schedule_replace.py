from fastapi import APIRouter
from fastapi import  HTTPException
from src.models.scheduleReplace import ScheduleReplace_Base, ScheduleReplace_Controller, SendSchedule_Base
from src.endpoints.send_to_device import publish_to_mqtt
import json

router = APIRouter(
    prefix="/schedule_replace",
    tags=["schedule_replace"],
    responses={404: {"description": "Not found"}},
)




@router.post("/add/")
async def add(user: ScheduleReplace_Base):
    db_control = ScheduleReplace_Controller()
    result = db_control.add(user.dict())
    return result

@router.put("/update/{id}")
async def update(user: ScheduleReplace_Base, id: int):
    db_control = ScheduleReplace_Controller()
    result = db_control.update(user.dict(), id)
    return result

@router.delete("/delete/{id}")
async def delete(id: int):
    db_control = ScheduleReplace_Controller()
    result = db_control.delete(id)
    return result


@router.post("/send_replace_delete/")
async def send_schedule(schedule: SendSchedule_Base):
    topic = f"mq_replace_delete/"
    message = json.dumps(schedule.model_dump())
    try:
        publish_to_mqtt(topic, message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"success": True, "topic": topic, "schedule_id": schedule.id}


@router.get("/update_schedule_status/")
async def update_schedule_status():
    topic = f"mq_update_schedule/"
    try:
        publish_to_mqtt(topic)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"success": True, "topic": topic}
   