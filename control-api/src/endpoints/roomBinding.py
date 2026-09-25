from fastapi import APIRouter
from fastapi import  HTTPException
from src.models.roomBinding import RoomBinding_Base,RoomBinding_Controller 

router = APIRouter(
    prefix="/room-binding",
    tags=["room-binding"],
    responses={404: {"description": "Not found"}},
)


@router.post("/add")
async def add_room_usage(room_binding: RoomBinding_Base):
    db = RoomBinding_Controller()
    result = db.add(room_binding.dict())
    if not result:
        raise HTTPException(status_code=400, detail="Failed to add room usage")
    return {"message": "Room usage added successfully", "id": result}   

@router.put("/update/{id}")
async def update_room_usage(id: int, room_binding: RoomBinding_Base):
    db = RoomBinding_Controller()
    result = db.update(room_binding.dict(), id)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to update room usage")
    return {"message": "Room usage updated successfully"}  


@router.get("/get_by_room/{room_no}")
async def get_by_room(room_no:str):
    db = RoomBinding_Controller()
    results = db.get_by_room(room_no)
    return results
   

