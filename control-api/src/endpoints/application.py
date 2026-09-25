from fastapi import APIRouter, Query
from fastapi import  HTTPException
from src.models.application import  Application_Controller,Application_Base,Application_Child
from src.util.dbcontroller import DBController as DB
from datetime import date, datetime, timedelta
from fastapi import HTTPException



router = APIRouter(
    prefix="/application",
    tags=["application"],
    responses={404: {"description": "Not found"}},
)

@router.post("/set_application/")
async def set_application(application_trans:Application_Child):
    db =Application_Controller()
    result=db.set(application_trans)
    return result

@router.delete("/unset_application/")
async def unset_application(room_no: str, application: str):
    db = Application_Controller()
    result = db.unset(room_no, application)
    return result

@router.get("/get_list_application/")
async def get_list_application(room_no: str="27.03.05"):       
    db=Application_Controller()
    results=db.get_list_application(room_no=room_no)
    del db 
    return results

@router.get("/get_list_application_usage/")
async def get_list_application_usage(room_no: str):
    db=Application_Controller()
    results=db.get_list_application_usage(room_no)
    del db 
    return results  