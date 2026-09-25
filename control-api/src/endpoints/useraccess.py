from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi import  HTTPException
from src.models.useraccess import UserAccess_Base, UserAccess_Controller


router = APIRouter(
    prefix="/user_access",
    tags=["user_access"],
    responses={404: {"description": "Not found"}},
)

@router.get("/is_exist/{user_name}")
async def is_exist(user_name: str):
    db_control = UserAccess_Controller()
    result = db_control.is_exist(user_name)
    return {"exists": result}   

@router.post("/add/")
async def add(user: UserAccess_Base):
    db_control = UserAccess_Controller()
    result = db_control.add(user.dict())
    return result

@router.put("/update/{id}")
async def update(user: UserAccess_Base, id: int):
    db_control = UserAccess_Controller()
    result = db_control.update(user.dict(), id)
    return result

@router.delete("/delete/{id}")
async def delete(id: int):
    db_control = UserAccess_Controller()
    result = db_control.delete(id)
    return result



@router.get("/change_pin/{user_name}")
async def change_pin(user_name: str, new_pin: str):
    db_control = UserAccess_Controller()
    result = db_control.change_pin(user_name, new_pin)
    return result