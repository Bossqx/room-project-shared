
from calendar import weekday
from datetime import datetime
from multiprocessing.connection import Client
from shlex import quote
from pydantic import BaseModel
from src.util.dbcontroller import DBController as DB

class RoomBinding_Base(BaseModel):
    room_no:str 
    ip_address:str 
    device:str 
    pin:int
    active_status:str="on"
    inactive_status:str="off" 


class RoomBinding_Controller():
    __tablename__ = 'room_binding'

    def __init__(self):
        self.__tableName__ = 'room_binding'

    
    def add(self, room_binding):
        result = db.create(room_binding)
        del db
        return result
    

        
    def update(self, room_binding,id):
        db = DB(self.__tableName__)
        result = db.update(room_binding, id)
        del db
        return result
    

    def get_by_room(self,room_no):
        db=DB()
        sql=f"""SELECT 
            room_no,
            ip_address,
            devices,
            pin,
            active_status
        FROM room_binding WHERE room_no=%s"""
        params=(room_no,)
        results=db.get_specific_sql(sql,None,params)
        del db 
        return results 
