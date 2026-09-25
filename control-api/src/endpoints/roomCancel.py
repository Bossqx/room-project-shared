from fastapi import APIRouter
from fastapi import  HTTPException
from src.models.roomCancel import RoomCancel_Base,RoomCancel_Controller 

router = APIRouter(
    prefix="/room-cancel",
    tags=["room-cancel"],
    responses={404: {"description": "Not found"}},
)


@router.post("/cancel_room")
async def add(room_cancel: RoomCancel_Base):
    db = RoomCancel_Controller()
    result = db.add(room_cancel.dict())
    if not result:
        raise HTTPException(status_code=400, detail="Failed to add room usage")
    return result    
