import os
from fastapi import APIRouter, Query
from fastapi import  HTTPException
from fastapi.responses import FileResponse
from src.models.accessory import  Accessory_Controller,Accessory_Base,Accessory_Child
from src.util.dbcontroller import DBController as DB
from datetime import date, datetime, timedelta
from fastapi import HTTPException



router = APIRouter(
    prefix="/accessory",
    tags=["accessory"],
    responses={404: {"description": "Not found"}},
)

ACCESSORIES_DIR = "ACCESSORIES_DIR"
os.makedirs(ACCESSORIES_DIR, exist_ok=True)

@router.post("/set_accessory/")
async def set_accessory(accessory_trans:Accessory_Child):
    db =Accessory_Controller()
    result=db.set(accessory_trans)
    return result



@router.delete("/unset_accessory/")
async def unset_accessory(room_no: str, accessory: str):
    db = Accessory_Controller()
    result = db.unset(room_no, accessory)
    return result

@router.get("/get_list_accessory/")
async def get_list_accessory(room_no: str="27.03.04"):       
    db=Accessory_Controller()
    results=db.get_list_accessories(room_no=room_no)
    del db 
    return results

@router.get("/get_list_accessory_usage/")
async def get_list_accessory_usage(room_no: str):
    db=Accessory_Controller()
    results=db.get_list_accessory_usage(room_no)
    del db
    return results

@router.get("/get_picture/{filename}")
async def get_picture(filename: str):
    file_path = os.path.join(ACCESSORIES_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Picture not found")
    return FileResponse(path=file_path)