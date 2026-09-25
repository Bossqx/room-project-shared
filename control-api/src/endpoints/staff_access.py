from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse
from fastapi import  HTTPException
from datetime import datetime
import json
from src.models.staffAccess import StaffAccess_Base, StaffAccess_Controller
from src.endpoints.send_to_device import publish_to_mqtt

router = APIRouter(
    prefix="/staff_access",
    tags=["staff_access"],
    responses={404: {"description": "Not found"}},
)

@router.get("/check_pin_count/{user_code}")
async def check_pin_out(user_code:str ):
    db = StaffAccess_Controller()
    result = db.check_pin_count(user_code)
    del db
    return result

@router.get("/increase_pin_count/{user_code}")
async def increase_pin_count(user_code:str ):
    db = StaffAccess_Controller()
    result = db.increase_pin_count(user_code)
    del db
    return result

@router.post("/add")
async def add(staff_access: StaffAccess_Base):
    db = StaffAccess_Controller()
    result = db.add(staff_access.dict())
    del db
    payload = json.dumps({
        "room_no": staff_access.room_no,
        "status": "staff_access_on",
        "date":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    publish_to_mqtt(f"staff_access/", payload)
    return result


@router.get("/update_status/{room_no}")
async def update_status(room_no: str, status_active: int):
    db = StaffAccess_Controller()
    result = db.update_status(room_no, status_active)
    #if status_active == 0:
    # payload = json.dumps({
    #     "room_no": room_no,
    #     "status": "off",
    #     "date":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    # })
    #publish_to_mqtt(f"staff_access/update_status/", payload)
    # else:
    #     payload = json.dumps({
    #         "room_no": room_no,
    #         "status": "on",
    #         "date":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    #     })
    #     publish_to_mqtt(f"staff_access/update_status/", payload)

    if not result:
        raise HTTPException(status_code=400, detail="Failed to update staff access status")
    return {"message": "Staff access status updated successfully"}
    # return {"message": "Staff access status updated successfully","payload":payload}